"""Public AI contract. Business authorization and deterministic actions live elsewhere."""

from app.ai.intent import classify, trained_model
from app.ai.retrieval import retrieve, retrieval_status, warmup_retrieval


def warmup() -> dict:
    """Prepare only local models; safe to call in a startup worker thread."""
    trained_model()
    warmup_retrieval()
    return status()


async def answer(question: str, evidence: list[dict], facts: dict | None = None) -> dict:
    from app.config import settings
    from app.ai.openrouter import OpenRouterAnswerer

    return await OpenRouterAnswerer(settings).answer(question, evidence, facts)


def status() -> dict:
    from app.config import settings

    return {"classifier": "tfidf_logistic_regression_v1_with_rules", "retrieval": retrieval_status(),
            "model": settings.openrouter_model if settings.llm_mode == "openrouter" else None}


__all__ = ["classify", "retrieve", "answer", "status", "warmup"]
