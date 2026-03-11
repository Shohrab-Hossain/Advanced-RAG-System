"""
Hybrid Retrieval Node
-----------------------
Runs three retrieval strategies in parallel and returns their results
as separate lists (merged later by the aggregator node).

  Vector  — dense semantic search via ChromaDB + sentence-transformers
  BM25    — sparse keyword search via rank-bm25
  Graph   — entity-graph traversal via GraphRAG (NetworkX)

Emits: stage_start → retrieval_result (or stage_skip when retrieve=False)
"""

import os
from ..state import RAGState
from ..core.events import emit
from .vector.vector_store import vector_store
# keyword/BM25 retrieval is now under the keyword subpackage
from .keyword.bm25_store import bm25_store
from .graph.graph_store import graph_store

TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "10"))


def retrieval_node(state: RAGState) -> dict:
    session_id = state.get("session_id")
    query = state["query"]

    if not state.get("retrieve", True):
        emit(session_id, "stage_skip", {
            "stage": "retrieval",
            "message": "Retrieval skipped — direct answer mode",
        })
        return {"vector_docs": [], "bm25_docs": [], "graph_docs": []}

    emit(session_id, "stage_start", {
        "stage": "retrieval",
        "message": "Running hybrid retrieval — Vector + BM25 + GraphRAG...",
    })

    vector_docs = vector_store.search(query, top_k=TOP_K)
    bm25_docs = bm25_store.search(query, top_k=TOP_K)
    graph_docs = graph_store.search(query, top_k=max(TOP_K // 2, 3))

    emit(session_id, "retrieval_result", {
        "stage": "retrieval",
        "vector_count": len(vector_docs),
        "bm25_count": len(bm25_docs),
        "graph_count": len(graph_docs),
        "message": (
            f"Vector: {len(vector_docs)} | "
            f"BM25: {len(bm25_docs)} | "
            f"Graph: {len(graph_docs)}"
        ),
    })

    return {
        "vector_docs": vector_docs,
        "bm25_docs": bm25_docs,
        "graph_docs": graph_docs,
    }
