"""Approved-document retrieval with a local model and explicit offline fallback."""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

ROOT = Path(__file__).resolve().parents[3]
MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
MODEL_PATH = ROOT / ".local" / "model-cache" / "all-MiniLM-L6-v2"
logger = logging.getLogger(__name__)
_mode = "not_loaded"


@lru_cache(maxsize=1)
def local_model():
    """Loading never downloads files or permits custom remote model code."""
    global _mode
    from app.config import settings

    if (settings.embedding_mode != "local" or settings.embedding_model != MODEL_ID
            or not (MODEL_PATH / "modules.json").exists()):
        _mode = "tfidf_fallback"
        return None
    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(
            str(MODEL_PATH), device="cpu", local_files_only=True, trust_remote_code=False,
        )
        _mode = "local_sentence_transformer"
        return model
    except Exception:
        # Optional ML libraries can raise backend-specific errors for corrupt
        # caches or unsupported runtimes. They must not disable support chat.
        logger.warning("Local embedding model unavailable; using TF-IDF retrieval")
        _mode = "tfidf_fallback"
        return None


def retrieval_status() -> str:
    if _mode == "not_loaded":
        from app.config import settings

        if (settings.embedding_mode == "local" and settings.embedding_model == MODEL_ID
                and (MODEL_PATH / "modules.json").exists()):
            return "local_model_cached_not_loaded"
        return "tfidf_fallback"
    return _mode


def warmup_retrieval() -> None:
    """Load and exercise optional local inference before application readiness."""
    global _mode
    model = local_model()
    if model is not None:
        try:
            model.encode(["Synthetic store support policy"], normalize_embeddings=True, show_progress_bar=False)
        except Exception:
            logger.warning("Local embedding warmup failed; using TF-IDF retrieval")
            _mode = "tfidf_fallback"


@lru_cache(maxsize=8)
def _document_vectors(texts: tuple[str, ...]):
    model = local_model()
    if model is not None:
        return model.encode(list(texts), normalize_embeddings=True, show_progress_bar=False)
    return None


def retrieve(text: str, documents: list[dict]) -> list[dict]:
    global _mode
    # Approval defines the active document. A new draft must not hide the
    # previous approved version. The admin service deactivates prior approvals
    # transactionally when it approves a replacement.
    candidates = [
        doc for doc in documents
        if doc.get("approved") is True and doc.get("id") and doc.get("content")
    ]
    if not candidates or not text.strip():
        return []
    # The caller supplies current versions; this also resolves duplicate keys.
    current: dict[str, dict] = {}
    for doc in candidates:
        key = str(doc.get("key") or doc["id"])
        if key not in current or int(doc.get("version", 1)) > int(current[key].get("version", 1)):
            current[key] = doc
    approved = list(current.values())
    texts = tuple(f"{doc.get('title', '')}. {doc['content'][:5000]}" for doc in approved)
    model = None if _mode == "tfidf_fallback" else local_model()
    scores = None
    if model is not None:
        try:
            vectors = _document_vectors(texts)
            query = model.encode([text[:3000]], normalize_embeddings=True, show_progress_bar=False)[0]
            scores = np.asarray(vectors @ query)
            minimum = 0.30
        except Exception:
            logger.warning("Local embedding inference failed; using TF-IDF retrieval")
            _mode = "tfidf_fallback"
    if scores is None:
        vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english", sublinear_tf=True)
        try:
            vectors = vectorizer.fit_transform(texts)
            query = vectorizer.transform([text[:3000]])
            scores = (vectors @ query.T).toarray().ravel()
        except ValueError:  # Empty vocabulary is an evidence miss, not an API error.
            return []
        minimum = 0.08
    ranked = sorted(enumerate(scores), key=lambda pair: (-float(pair[1]), str(approved[pair[0]]["id"])))
    return [
        {"id": str(approved[index]["id"]), "title": approved[index].get("title", "Policy"),
         "version": approved[index].get("version", 1), "content": approved[index]["content"],
         "score": round(float(score), 4)}
        for index, score in ranked[:3] if float(score) >= minimum
    ]
