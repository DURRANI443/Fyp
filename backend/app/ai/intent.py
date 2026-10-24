"""Reproducible local intent model; no network and no downloaded pickle files.

Only the fixed training split is fitted. High precision rules are separately
reported so evaluation can compare the learned model with the hybrid router.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline

ROOT = Path(__file__).resolve().parents[3]
DATASET = ROOT / "data" / "intents" / "v1" / "dataset.json"
LABELS = ("tracking", "return", "cancel", "product", "policy", "damage", "billing", "human", "unknown")
PRIORITY = ("human", "damage", "billing", "cancel", "return", "tracking", "product", "policy")
CONFIDENCE_THRESHOLD = 0.22  # Selected by macro-F1 on the fixed validation groups only.

# Deliberately simple baseline. It is not used to authorize any operation.
KEYWORDS = {
    "human": ("human", "agent", "person", "manager", "supervisor"),
    "damage": ("damaged", "broken", "faulty", "wrong item", "missing", "torn"),
    "billing": ("payment", "charged", "refund", "invoice", "card", "bill"),
    "cancel": ("cancel", "stop my order", "stop the order"),
    "return": ("return", "exchange", "send it back"),
    "tracking": ("track", "where is", "shipment", "parcel", "delivery", "shipped"),
    "product": ("product", "size", "recommend", "material", "stock", "shirt", "jacket"),
    "policy": ("policy", "terms", "warranty", "privacy"),
}

PATTERNS = {
    "human": r"\b(?:human|real person|support agent|representative|supervisor|manager|staff member|customer care|support person)\b|\b(?:talk|speak|connect|transfer|assign|escalate)\b.{0,35}\b(?:person|staff|team|someone|employee)\b|\b(?:stop|no more)\b.{0,20}\b(?:bot|automated)\b",
    "damage": r"\b(?:damaged|broken|faulty|defect(?:ive)?|torn|cracked|stain|hole)\b|\bwrong (?:item|size|color|colour|product)\b.{0,35}\b(?:sent|received|delivered)\b|\b(?:sent|received|delivered)\b.{0,35}\bwrong (?:item|size|color|colour|product)\b|\b(?:item|product|strap|hood|belt)\b.{0,30}\bmissing\b|\bmissing\b.{0,30}\b(?:item|product|from|box)\b|\b(?:parcel|package|box)\b.{0,20}\bempty\b",
    "billing": r"\b(?:charged|charge|payment|invoice|receipt|billed|billing|bank statement|card declined|declined card)\b|\b(?:where|waiting|status|approved|reached|receive|received)\b.{0,30}\brefund\b|\brefund\b.{0,30}\b(?:bank|status|arrive|arrived|credited)\b",
    "cancel": r"\bcancel(?:lation|led)?\b|\b(?:stop|halt|withdraw|revoke|call off)\b.{0,30}\b(?:order|purchase|shipment)\b",
    "return": r"\b(?:return|exchange|swap)\b|\bsend\b.{0,20}\bback\b|\bgive back\b",
    "tracking": r"\btrack(?:ing)?\b|\bwhere\b.{0,20}\b(?:order|parcel|package|shipment)\b|\b(?:delivery|shipment|order|parcel|package)\b.{0,35}\b(?:late|overdue|delayed|arrive|arrived|status|stuck|way|shipped)\b|\b(?:late|delayed|overdue)\b.{0,20}\b(?:order|delivery|shipment|parcel)\b|\b(?:courier|carrier|driver|dispatch|depot|sorting facility)\b",
    "product": r"\b(?:recommend|suggest|compare|in stock|available products|sizing guide|material|waterproof|features|care instructions)\b|\bwhat sizes\b|\bhow much\b.{0,30}\b(?:cost|shirt|jacket|bag|shoes)\b",
    "policy": r"\b(?:policy|policies|terms|warranty|guarantee|privacy|general rules)\b|\b(?:how many days|how long)\b.{0,40}\b(?:return|shipping|guarantee)\b|\b(?:return|exchange|shipping|delivery)\b.{0,25}\b(?:conditions|rules)\b",
}


def load_dataset() -> dict:
    return json.loads(DATASET.read_text(encoding="utf-8"))


def split_rows(split: str) -> list[dict]:
    return [
        {"id": f"{group['id']}_{index + 1}", "group": group["id"], "intent": group["intent"], "text": text}
        for group in load_dataset()["groups"] if group["split"] == split
        for index, text in enumerate(group["utterances"])
    ]


@lru_cache(maxsize=1)
def trained_model() -> Pipeline:
    rows = split_rows("train")
    model = Pipeline([
        ("features", FeatureUnion([
            ("word", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, strip_accents="unicode")),
            ("character", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True)),
        ], transformer_weights={"word": 1.0, "character": 0.55})),
        ("classifier", LogisticRegression(C=6.0, class_weight="balanced", max_iter=1000, random_state=42)),
    ])
    model.fit([row["text"] for row in rows], [row["intent"] for row in rows])
    return model


def keyword_intent(text: str) -> str:
    normalized = text.lower()
    for intent, words in KEYWORDS.items():
        if any(re.search(r"\b" + re.escape(word) + r"\b", normalized) for word in words):
            return intent
    return "unknown"


def learned_intent(text: str, threshold: float = CONFIDENCE_THRESHOLD) -> dict:
    text = text.strip()[:3000]
    if not text:
        return {"intent": "unknown", "confidence": 0.0, "source": "classifier", "intents": ["unknown"]}
    model = trained_model()
    probabilities = model.predict_proba([text])[0]
    best = int(probabilities.argmax())
    confidence = float(probabilities[best])
    intent = str(model.classes_[best]) if confidence >= threshold else "unknown"
    return {"intent": intent, "confidence": round(confidence, 4), "source": "classifier", "intents": [intent]}


def rule_intents(text: str) -> list[str]:
    normalized = text.lower().replace("’", "'")[:3000]
    hits = {intent for intent, pattern in PATTERNS.items() if re.search(pattern, normalized)}
    # A general policy question must not become an order-changing request.
    if "policy" in hits and not re.search(r"\b(?:i want|i need|please|my order|my item|my purchase)\b", normalized):
        hits.difference_update({"cancel", "return", "tracking", "product"})
    # Scope simple explicit negation to its clause rather than executing the verb.
    for intent, word in (("cancel", "cancel"), ("return", "return"), ("human", "human")):
        if re.search(r"\b(?:do not|don't|not to|no need to)\s+(?:want to\s+)?" + word + r"\b", normalized):
            hits.discard(intent)
    return [intent for intent in PRIORITY if intent in hits]


def classify(text: str, threshold: float = CONFIDENCE_THRESHOLD) -> dict:
    result = learned_intent(text, threshold)
    hits = rule_intents(text)
    if hits:
        # Rule confidence is deliberately not represented as a calibrated ML probability.
        return {"intent": hits[0], "confidence": result["confidence"], "source": "hybrid_rules", "intents": hits}
    if re.search(r"\b(?:do not|don't|not to|no need to)\s+(?:want to\s+)?(?:cancel|return)\b", text.lower()):
        return {"intent": "unknown", "confidence": result["confidence"], "source": "negation_guard", "intents": ["unknown"]}
    return result
