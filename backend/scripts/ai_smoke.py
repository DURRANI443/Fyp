"""Local AI smoke by default; --live is the explicit, separate API-key check.

Never prints an API key, request body, customer information, or generated text.
The live path sends only the synthetic return-policy example defined here.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ai.engine import classify, retrieve, status
from app.ai.openrouter import OpenRouterAnswerer
from app.config import settings

ROOT = Path(__file__).resolve().parents[2]


def local_smoke() -> dict:
    fixture = json.loads((ROOT / "data" / "retrieval" / "v1" / "cases.json").read_text(encoding="utf-8"))
    results = []
    for case in fixture["queries"]:
        start = time.perf_counter()
        matches = retrieve(case["text"], fixture["documents"])
        predicted = matches[0]["id"] if matches else None
        results.append({**case, "predicted": predicted, "correct": predicted == case["expected"],
                        "latency_ms": round((time.perf_counter() - start) * 1000, 2)})
    return {"status": status(), "retrieval_top_1_accuracy": sum(row["correct"] for row in results) / len(results),
            "retrieval_cases": results,
            "mixed_intent": classify("My order is late and I want to cancel it"),
            "limitation": "Tiny synthetic smoke corpus, not an independent retrieval benchmark. First query includes cold model load."}


async def live_smoke() -> dict:
    if not settings.openrouter_api_key.strip():
        return {"status": "not_run", "reason": "api_key_missing", "model": settings.openrouter_model}
    configured = settings.model_copy(update={"llm_mode": "openrouter"})
    result = await OpenRouterAnswerer(configured).answer("What is the return window?", [{
        "id": "synthetic-returns", "title": "Synthetic return policy", "version": 1,
        "content": "Unused items with tags can be returned within 30 days after delivery.",
    }])
    return {"status": "passed" if result["text"] else "failed", "reason": result["reason"],
            "mode": result["mode"], "model": result["model"], "prompt": "grounded-policy-v1"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="Explicitly test configured free OpenRouter route using synthetic policy data")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = asyncio.run(live_smoke()) if args.live else local_smoke()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "retrieval_cases"}, indent=2))
    if args.live and report["status"] != "passed":
        raise SystemExit(2)
