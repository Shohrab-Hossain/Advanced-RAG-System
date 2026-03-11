"""
Cross-Encoder Reranker Node
-----------------------------
Scores every (query, document) pair with a cross-encoder model and
returns the top-k highest-scoring documents as the final context.

Model: cross-encoder/ms-marco-MiniLM-L-6-v2  (fast, accurate)

Falls back to score-sorted top-k if the model can't be loaded.

Emits: stage_start → stage_complete | stage_error
"""

import os
from typing import List

from ..state import RAGState
from ..core.events import emit

RERANKER_MODEL = os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
RERANK_TOP_K = int(os.getenv("RERANK_TOP_K", "5"))

_reranker = None


def _get_reranker():
    global _reranker
    if _reranker is None:
        from sentence_transformers import CrossEncoder
        _reranker = CrossEncoder(RERANKER_MODEL)
    return _reranker


def reranker_node(state: RAGState) -> dict:
    session_id = state.get("session_id")
    query = state["query"]
    all_docs: List[dict] = state.get("all_docs", [])

    emit(session_id, "stage_start", {
        "stage": "reranker",
        "message": f"Cross-encoder scoring {len(all_docs)} candidates → top {RERANK_TOP_K}...",
    })

    if not all_docs:
        emit(session_id, "stage_complete", {
            "stage": "reranker",
            "message": "No documents to rerank",
        })
        return {"context": []}

    try:
        reranker = _get_reranker()
        pairs = [(query, doc["content"]) for doc in all_docs]
        scores = reranker.predict(pairs)

        scored = [
            {**doc, "rerank_score": float(score)}
            for doc, score in zip(all_docs, scores)
        ]
        scored.sort(key=lambda d: d["rerank_score"], reverse=True)
        top = scored[:RERANK_TOP_K]

        emit(session_id, "stage_complete", {
            "stage": "reranker",
            "top_k": len(top),
            "scores": [round(d["rerank_score"], 4) for d in top],
            "sources": [d.get("source") for d in top],
            "message": f"Selected top {len(top)} documents by cross-encoder score",
        })
        return {"context": top}

    except Exception as e:
        emit(session_id, "stage_error", {"stage": "reranker", "error": str(e)})
        fallback = sorted(all_docs, key=lambda d: d.get("score", 0), reverse=True)[:RERANK_TOP_K]
        return {"context": fallback}
