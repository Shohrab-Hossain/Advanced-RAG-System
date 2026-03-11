"""
RAG Pipeline State Definition
------------------------------
Single TypedDict that flows through every LangGraph node.
Each node reads what it needs and returns only what it modifies.
"""

from typing import TypedDict, List, Optional, Any


class Document(TypedDict):
    """Represents a retrieved piece of evidence."""
    content: str
    metadata: dict        # file_name, page, url, etc.
    score: float          # initial retrieval score
    source: str           # "vector" | "bm25" | "graph" | "web"
    rerank_score: float   # cross-encoder score (set by reranker node)


class RAGState(TypedDict):
    # ── Input ────────────────────────────────────────────────────────────────
    query: str
    session_id: Optional[str]          # Used to route SSE events
    provider: str                      # "openai" | "ollama"
    ollama_model: Optional[str]        # User-selected Ollama model (overrides env default)

    # ── Planner outputs ──────────────────────────────────────────────────────
    retrieve: bool                     # Should we hit the knowledge base?
    use_external: bool                 # Should we run a web search?
    query_type: str                    # "factual" | "analytical" | "conversational"

    # ── Retrieval outputs ────────────────────────────────────────────────────
    vector_docs: List[Document]        # Dense (ChromaDB) results
    bm25_docs: List[Document]          # Sparse (BM25) results
    graph_docs: List[Document]         # GraphRAG traversal results
    web_docs: List[Document]           # Web / external search results

    # ── Aggregation ──────────────────────────────────────────────────────────
    all_docs: List[Document]           # Deduplicated union of all sources

    # ── Reranking ────────────────────────────────────────────────────────────
    context: List[Document]            # Top-k after cross-encoder reranking

    # ── Compression ──────────────────────────────────────────────────────────
    compressed_context: str            # LLM-compressed context string

    # ── Generation ───────────────────────────────────────────────────────────
    answer: str                        # Raw generated answer
    sources: List[dict]                # Source metadata for citations

    # ── Reflection ───────────────────────────────────────────────────────────
    grounded: bool                     # Is the answer grounded in context?
    reflection_feedback: str           # Specific feedback from reflection agent
    retry_count: int                   # How many retrieval retries so far

    # ── Final output ─────────────────────────────────────────────────────────
    final_answer: str                  # Answer after reflection (may add caveats)
    final_sources: List[dict]          # Sources accompanying the final answer
    pipeline_metadata: dict            # Stats: confidence, retries, grounded, etc.
