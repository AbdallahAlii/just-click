from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from cmcp.config.settings import settings
from cmcp.core.exceptions import BusinessValidationError


def _backend_root() -> Path:
    return Path(__file__).resolve().parents[5]


def _chroma_dir() -> Path:
    chroma_dir = Path(settings.CHATBOT_CHROMA_DIR)
    if not chroma_dir.is_absolute():
        chroma_dir = _backend_root() / settings.CHATBOT_CHROMA_DIR
    chroma_dir.mkdir(parents=True, exist_ok=True)
    return chroma_dir


def _disable_chroma_telemetry() -> None:
    os.environ["ANONYMIZED_TELEMETRY"] = "False"
    os.environ.setdefault("CHROMA_TELEMETRY", "FALSE")


@lru_cache(maxsize=1)
def get_collection():
    _disable_chroma_telemetry()

    try:
        import chromadb
        from chromadb.config import Settings as ChromaSettings
    except Exception as exc:
        raise BusinessValidationError("chromadb is not installed.") from exc

    client = chromadb.PersistentClient(
        path=str(_chroma_dir()),
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    return client.get_or_create_collection(
        name=settings.CHATBOT_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def add_chunks(
    *,
    chunks: list[str],
    vectors: list[list[float]],
    metadatas: list[dict[str, Any]],
    ids: list[str],
) -> None:
    coll = get_collection()
    coll.add(documents=chunks, embeddings=vectors, metadatas=metadatas, ids=ids)


def query_chunks(
    *,
    query_vector: list[float],
    where_filter: dict[str, Any],
    n_results: int,
) -> tuple[list[str], list[dict[str, Any]], list[float]]:
    coll = get_collection()
    res = coll.query(
        query_embeddings=[query_vector],
        n_results=n_results,
        where=where_filter,
        include=["documents", "metadatas", "distances"],
    )
    return (
        res.get("documents", [[]])[0],
        res.get("metadatas", [[]])[0],
        res.get("distances", [[]])[0],
    )


def get_material_chunks(
    *,
    company_id: int,
    material_id: int,
    chunk_indices: list[int] | None = None,
) -> tuple[list[str], list[dict[str, Any]]]:
    coll = get_collection()
    filters: list[dict[str, Any]] = [
        {"company_id": int(company_id)},
        {"material_id": int(material_id)},
    ]
    if chunk_indices is not None:
        filters.append({"chunk_index": {"$in": [int(i) for i in chunk_indices]}})
    where: dict[str, Any] = {"$and": filters} if len(filters) > 1 else filters[0]
    res = coll.get(
        where=where,
        include=["documents", "metadatas"],
    )
    return res.get("documents") or [], res.get("metadatas") or []


def delete_material_chunks(company_id: int, material_id: int) -> int:
    coll = get_collection()
    res = coll.get(
        where={"$and": [{"company_id": int(company_id)}, {"material_id": int(material_id)}]},
        include=[],
    )
    ids = res.get("ids") or []
    if ids:
        coll.delete(ids=ids)
    return len(ids)


def delete_company_chunks(company_id: int) -> int:
    coll = get_collection()
    res = coll.get(where={"company_id": int(company_id)}, include=[])
    ids = res.get("ids") or []
    if ids:
        coll.delete(ids=ids)
    return len(ids)


def release_vector_store() -> None:
    get_collection.cache_clear()
