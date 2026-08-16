from __future__ import annotations

import os

# Force CPU before torch/sentence-transformers import (avoids slow CUDA probe on old drivers).
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from functools import lru_cache
from pathlib import Path

from cmcp.config.settings import settings
from cmcp.core.exceptions import BusinessValidationError


def _backend_root() -> Path:
    return Path(__file__).resolve().parents[5]


def _cache_dir() -> Path:
    cache = Path(settings.CHATBOT_EMBEDDING_CACHE_DIR)
    if not cache.is_absolute():
        cache = _backend_root() / settings.CHATBOT_EMBEDDING_CACHE_DIR
    return cache


def _model_local_path() -> Path:
    model_name = settings.CHATBOT_EMBEDDING_MODEL.replace("/", "--")
    return _cache_dir() / model_name


def embedding_model_ready() -> bool:
    local = _model_local_path()
    if not local.is_dir():
        return False
    return any(local.iterdir())


@lru_cache(maxsize=1)
def get_embedding_model():
    local = _model_local_path()
    if not local.is_dir() or not any(local.iterdir()):
        if settings.CHATBOT_ALLOW_RUNTIME_MODEL_DOWNLOAD:
            from sentence_transformers import SentenceTransformer

            local.parent.mkdir(parents=True, exist_ok=True)
            model = SentenceTransformer(settings.CHATBOT_EMBEDDING_MODEL)
            model.save(str(local))
            return model
        raise BusinessValidationError(
            "Embedding model not found. Run: python scripts/download_embedding_model.py"
        )

    try:
        from sentence_transformers import SentenceTransformer
    except Exception as exc:
        raise BusinessValidationError("sentence-transformers is not installed.") from exc

    return SentenceTransformer(str(local), device=settings.CHATBOT_EMBEDDING_DEVICE)


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    model = get_embedding_model()
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return [vec.tolist() for vec in vectors]


def embed_query(query: str) -> list[float]:
    return embed_texts([query])[0]


def release_embedding_model() -> None:
    get_embedding_model.cache_clear()
    try:
        import gc

        gc.collect()
    except Exception:
        pass
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass
