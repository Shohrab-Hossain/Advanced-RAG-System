"""
Evidence Aggregator Node
-------------------------
Merges results from all retrieval sources (vector, BM25, graph, web)
into a single deduplicated list ordered by original score.

Deduplication is by MD5 of the content string — identical chunks
from different retrievers are kept only once (highest score wins).

Emits: stage_start → stage_complete
"""

import hashlib
from collections import defaultdict
from ..state import RAGState
from ..core.events import emit


def aggregator_node(state: RAGState) -> dict:
    session_id = state.get("session_id")

    emit(session_id, "stage_start", {
        "stage": "aggregator",
        "message": "Merging and deduplicating evidence from all sources...",
    })

    raw = (
        state.get("vector_docs", [])
        + state.get("bm25_docs", [])
        + state.get("graph_docs", [])
        + state.get("web_docs", [])
    )

    # Keep the copy with the highest score for each unique content hash
    best: dict[str, dict] = {}
    for doc in raw:
        h = hashlib.md5(doc["content"].encode("utf-8", errors="replace")).hexdigest()
        if h not in best or doc["score"] > best[h]["score"]:
            best[h] = doc

    unique_docs = sorted(best.values(), key=lambda d: d["score"], reverse=True)

    # Distribution for SSE payload
    source_counts: dict[str, int] = defaultdict(int)
    for doc in unique_docs:
        source_counts[doc.get("source", "unknown")] += 1

    emit(session_id, "stage_complete", {
        "stage": "aggregator",
        "before": len(raw),
        "after": len(unique_docs),
        "sources": dict(source_counts),
        "message": (
            f"{len(unique_docs)} unique docs "
            f"(from {len(raw)} total, "
            f"{len(raw) - len(unique_docs)} duplicates removed)"
        ),
    })

    return {"all_docs": unique_docs}
