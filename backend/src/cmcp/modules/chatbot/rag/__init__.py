from __future__ import annotations

from cmcp.modules.chatbot.rag.answer import answer_material_question, call_llm
from cmcp.modules.chatbot.rag.chunker import chunk_text
from cmcp.modules.chatbot.rag.embeddings import (
    embed_query,
    embed_texts,
    embedding_model_ready,
    get_embedding_model,
    release_embedding_model,
)
from cmcp.modules.chatbot.rag.extractor import compute_hash, material_filename, read_material_file
from cmcp.modules.chatbot.rag.indexer import index_material, normalize_label, semester_label
from cmcp.modules.chatbot.rag.modes import detect_mode
from cmcp.modules.chatbot.rag.retriever import get_material_context_chunks, get_relevant_chunks, material_where_filter
from cmcp.modules.chatbot.rag.vector_store import delete_company_chunks, delete_material_chunks, release_vector_store

__all__ = [
    "answer_material_question",
    "call_llm",
    "chunk_text",
    "compute_hash",
    "delete_company_chunks",
    "delete_material_chunks",
    "detect_mode",
    "embed_query",
    "embed_texts",
    "embedding_model_ready",
    "get_embedding_model",
    "get_material_context_chunks",
    "get_relevant_chunks",
    "index_material",
    "material_filename",
    "material_where_filter",
    "normalize_label",
    "read_material_file",
    "release_embedding_model",
    "release_vector_store",
    "semester_label",
]
