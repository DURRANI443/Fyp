"""Evaluate held-out synthetic intents. No API key or network calls are used.

Outputs JSON, including every held-out prediction and confusion matrix. The
small test set was authored alongside the implementation; this is an internal
demo evaluation, not an independently collected benchmark.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sklearn import __version__ as sklearn_version
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score

from app.ai.intent import (
    CONFIDENCE_THRESHOLD, DATASET, LABELS, classify, keyword_intent, learned_intent,
    load_dataset, split_rows, trained_model,
)

TEAM_MAP = {"tracking": "logistics", "return": "returns", "damage": "returns", "billing": "billing",
            "cancel": "general", "product": "general", "policy": "general", "human": "general", "unknown": "general"}


def split_audit() -> dict:
    groups = load_dataset()["groups"]
    ids = [group["id"] for group in groups]
    assert len(ids) == len(set(ids)), "A group appears in more than one split"
    rows = [(group["split"], text.lower().strip()) for group in groups for text in group["utterances"]]
    assert len(rows) == len({text for _, text in rows}), "Exact duplicate messages exist"
    # Report simple lexical near-overlap; semantic leakage requires independent review.
    overlaps = []
    for index, (split, text) in enumerate(rows):
        words = set(text.split())
        for other_split, other_text in rows[index + 1:]:
            if split == other_split:
                continue
            other_words = set(other_text.split())
            similarity = len(words & other_words) / max(1, len(words | other_words))
            if similarity >= 0.70:
                overlaps.append({"left": text, "right": other_text, "jaccard": round(similarity, 3)})
    return {"group_disjoint": True, "exact_duplicate_count": 0, "cross_split_token_jaccard_at_least_0_7": overlaps}


def evaluate() -> dict:
    trained_model()
    validation = split_rows("validation")
    validation_scores = []
    for threshold in (0.18, 0.22, 0.26, 0.28, 0.30, 0.34, 0.38, 0.42):
        predicted = [learned_intent(row["text"], threshold)["intent"] for row in validation]
        validation_scores.append({"threshold": threshold, "macro_f1": f1_score(
            [row["intent"] for row in validation], predicted, labels=list(LABELS), average="macro", zero_division=0,
        )})
    best = max(validation_scores, key=lambda result: (result["macro_f1"], result["threshold"]))
    threshold = best["threshold"]
    test = split_rows("test")
    actual = [row["intent"] for row in test]
    methods = {
        "keyword": lambda text: keyword_intent(text),
        "classifier": lambda text: learned_intent(text, threshold)["intent"],
        "hybrid": lambda text: classify(text, threshold)["intent"],
    }
    results = {}
    for name, predict in methods.items():
        start = time.perf_counter()
        predictions = [predict(row["text"]) for row in test]
        elapsed = time.perf_counter() - start
        results[name] = {
            "accuracy": accuracy_score(actual, predictions),
            "macro_f1": f1_score(actual, predictions, labels=list(LABELS), average="macro", zero_division=0),
            "mapped_team_accuracy": accuracy_score([TEAM_MAP[item] for item in actual], [TEAM_MAP[item] for item in predictions]),
            "latency_ms_per_message_warm": elapsed * 1000 / len(test),
            "per_class": classification_report(actual, predictions, labels=list(LABELS), output_dict=True, zero_division=0),
            "confusion_matrix": confusion_matrix(actual, predictions, labels=list(LABELS)).tolist(),
            "predictions": [{**row, "predicted": prediction, "correct": row["intent"] == prediction}
                            for row, prediction in zip(test, predictions)],
        }
    return {
        "evaluated_at_utc": datetime.now(timezone.utc).isoformat(), "dataset_version": "1.0.0",
        "dataset_sha256": hashlib.sha256(DATASET.read_bytes()).hexdigest(),
        "scikit_learn_version": sklearn_version, "seed": 42, "labels": list(LABELS),
        "model_parameters": {"word_ngrams": [1, 2], "character_word_boundary_ngrams": [3, 5],
                             "feature_weights": {"word": 1.0, "character": 0.55}, "logistic_C": 6.0,
                             "class_weight": "balanced", "max_iter": 1000,
                             "confidence_note": "Uncalibrated maximum logistic probability; hybrid rule outputs retain this score, not a rule certainty."},
        "split_counts": {split: dict(Counter(row["intent"] for row in split_rows(split)))
                         for split in ("train", "validation", "test")},
        "split_audit": split_audit(), "validation_threshold_search": validation_scores,
        "selected_threshold": threshold, "runtime_threshold": CONFIDENCE_THRESHOLD,
        "results": results,
        "limitations": [
            "234 synthetic single-turn messages: 144 training, 36 validation, 54 held-out test; six test messages per class.",
            "AI-assisted messages and labels; scenario groups are disjoint, but vocabulary and author style overlap; no independent annotator or real traffic.",
            "Rules and labels were authored by the same implementation team; hybrid results may be optimistic.",
            "Mapped team accuracy uses a static intent-to-team mapping, not contextual full-workflow routing correctness.",
            "No confidence intervals or production latency claims; local warm inference measured on this workstation.",
            "Live generative answer quality is not measured without an API key and an independently reviewed answer set.",
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DATASET.parents[3] / ".local" / "intent-evaluation.json")
    args = parser.parse_args()
    report = evaluate()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Saved evaluation to {args.output}")
    print(f"Validation-selected threshold: {report['selected_threshold']} (runtime {report['runtime_threshold']})")
    for method, metrics in report["results"].items():
        print(f"{method}: accuracy={metrics['accuracy']:.4f}, macro-F1={metrics['macro_f1']:.4f}, mapped team={metrics['mapped_team_accuracy']:.4f}")
