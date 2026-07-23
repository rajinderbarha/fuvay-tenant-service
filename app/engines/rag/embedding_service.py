"""RAG Engine — real local embedding provider.

MODULE-L5-51 decision record:
  - OPENAI_API_KEY is empty in this deployment (checked app/config.py + .env)
    so "text-embedding-3-small" was never actually reachable — the previous
    _mock_embed() was standing in for a provider that was never configured.
  - DeepSeek's public API (the only other LLM key configured — see
    DEEPSEEK_API_KEY) exposes only /v1/chat/completions
    (app/engines/ai_conversation/deepseek_client.py) — no embeddings
    endpoint exists to call.
  - Given no real embedding API is configured, the honest path is a LOCAL
    embedding model: `sentence-transformers` (new dependency, real and
    widely used, no API key required) running `all-MiniLM-L6-v2`
    (384-dim, ~80MB, CPU-friendly, well-known general-purpose model).
    This produces real, genuine semantic embeddings — not a mock.

The model is loaded once per process (module-level singleton) since loading
it is relatively expensive; encoding itself is fast on CPU for short chunks.
"""
from __future__ import annotations

import threading
from typing import Iterable

import structlog

from app.engines.rag.constants import EMBEDDING_DIMENSIONS, EMBEDDING_MODEL

logger = structlog.get_logger("rag.embedding")

_model = None
_model_lock = threading.Lock()


def _get_model():
    global _model
    if _model is not None:
        return _model
    with _model_lock:
        if _model is None:
            from sentence_transformers import SentenceTransformer
            logger.info("rag.embedding_model_loading", model=EMBEDDING_MODEL)
            _model = SentenceTransformer(EMBEDDING_MODEL)
            dim_fn = getattr(_model, "get_embedding_dimension", None) or _model.get_sentence_embedding_dimension
            logger.info("rag.embedding_model_loaded", model=EMBEDDING_MODEL, dim=dim_fn())
    return _model


def embed_text(text: str) -> list[float]:
    """Real embedding for a single string. Returns a plain python list of
    floats of length EMBEDDING_DIMENSIONS."""
    model = _get_model()
    vec = model.encode(text or "", normalize_embeddings=True)
    return [float(x) for x in vec]


def embed_batch(texts: Iterable[str]) -> list[list[float]]:
    """Real embedding for many strings in one batch call (faster than
    looping embed_text — used by the ingestion pipeline)."""
    texts = list(texts)
    if not texts:
        return []
    model = _get_model()
    vecs = model.encode(texts, normalize_embeddings=True, batch_size=32)
    return [[float(x) for x in v] for v in vecs]
