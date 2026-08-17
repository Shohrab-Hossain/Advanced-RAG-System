"""
Knowledge Base Services
-----------------------
The three-store work behind the knowledge-base routes.

Every ingest and every delete must touch ALL THREE stores AND the registry.
There are no transactions and no cross-store lock, so a partial write leaves the
corpus inconsistent with nothing surfaced — which is why the ordering here is
fixed and why the routes call these functions rather than reaching into a store.
"""

import os

from adrag.config import Config
from adrag.custom_packages.rag_pipeline.retrieval.stores.vector_store import vector_store
from adrag.custom_packages.rag_pipeline.retrieval.stores.bm25_store import bm25_store
from adrag.custom_packages.rag_pipeline.retrieval.stores.graph_store import graph_store
from adrag.custom_packages.rag_pipeline.ingestion.loader import load_file, generate_chunk_ids
from adrag.custom_packages.rag_pipeline.ingestion import registry as kb_registry


# ── Read ──────────────────────────────────────────────────────────────────────

def index_stats() -> dict:
    """Current totals across the three stores."""
    return {
        "vector_count": vector_store.count(),
        "bm25_count": bm25_store.count(),
        "graph": graph_store.get_stats(),
    }


def totals() -> dict:
    """The post-write shape the upload and delete responses report."""
    return {
        "vector_total": vector_store.count(),
        "bm25_total": bm25_store.count(),
        "graph": graph_store.get_stats(),
    }


# ── Write ─────────────────────────────────────────────────────────────────────

def index_document(file_path: str, filename: str, fallback_hash: str) -> tuple[dict, int]:
    """
    Load, chunk and index one uploaded file into all three stores + the registry.

    Returns (payload, chunk_count). Raises ValueError when no text can be extracted,
    which the route turns into a 422 — an empty index write would otherwise register
    a knowledge base nothing can retrieve.
    """
    texts, metadatas = load_file(file_path)
    if not texts:
        raise ValueError("No text could be extracted from this file")

    file_hash = metadatas[0].get("file_hash", fallback_hash)
    chunk_ids = generate_chunk_ids(file_hash, len(texts))

    # Remove any existing data for this file before re-indexing
    remove_document(file_hash)

    # Index into all three stores
    vector_store.add_documents(texts, metadatas, chunk_ids)
    bm25_store.add_documents(texts, metadatas)
    for i, (text, meta) in enumerate(zip(texts, metadatas)):
        graph_store.add_document(chunk_ids[i], text, meta)

    graph_stats = graph_store.get_stats()
    kb_entry = kb_registry.register(file_hash, filename, {
        "chunks": len(texts),
        "vectors": len(texts),   # 1 chunk → 1 embedding
        "entities": graph_store.count_entities_by_file(file_hash),
        "edges": graph_stats.get("edges", 0),
    })

    return {
        "success": True,
        "file_name": filename,
        "file_hash": file_hash,
        "chunks_indexed": len(texts),
        "kb": kb_entry,
        "stats": totals(),
    }, len(texts)


def remove_document(file_hash: str) -> None:
    """Drop one file from all three stores and the registry. Order is deliberate."""
    vector_store.delete_by_file(file_hash)
    bm25_store.delete_by_file(file_hash)
    graph_store.delete_by_file(file_hash)
    kb_registry.remove(file_hash)


def clear_everything() -> None:
    """Wipe all three stores, the registry, and every uploaded file on disk."""
    all_kbs = kb_registry.list_all()

    vector_store.clear()
    bm25_store.clear()
    graph_store.clear()
    kb_registry.clear_all()

    for kb in all_kbs:
        delete_upload(kb["name"])


def delete_upload(name: str) -> None:
    """Remove an uploaded file if it is still on disk. A missing file is not an error."""
    file_path = os.path.join(Config.UPLOAD_FOLDER, name)
    if os.path.isfile(file_path):
        try:
            os.remove(file_path)
        except OSError:
            pass
