# ADR-002: Three-store hybrid retrieval with cross-encoder reranking
Date: 2026-08-13 · Status: accepted

> Reconstructed from the code on 2026-08-13, not recorded at decision time. Grounded in
> `retrieval/node.py`, the three `*_store.py` modules, `ranking/aggregator.py`, and `ranking/reranker.py`.

## Context

A single retrieval strategy has a characteristic blind spot:

- **Dense vector search** captures paraphrase but misses exact identifiers, rare terms, and numbers whose
  embeddings sit nowhere near the query's.
- **BM25 keyword search** nails exact terms but fails entirely when the question and the document use
  different words for the same thing.
- **Neither** can follow a relationship that spans chunks — "what else mentions this entity" is not a
  similarity question.

Meanwhile, the score a retriever produces measures *proximity in its own space*, not *whether this passage
answers this question* — so more candidates from a single retriever does not mean better context.

## Decision

Run all three retrievers on every query with retrieval turned on (`retrieval/node.py`), keep their results
in separate state lists, merge them by deduplicating on content MD5 (highest score wins), and then rescore
**every** surviving candidate with a cross-encoder (`cross-encoder/ms-marco-MiniLM-L-6-v2`), keeping the
top `RERANK_TOP_K` (5). Retrieval optimises for **recall**; the cross-encoder supplies **precision**.

An optional fourth source — DuckDuckGo web search — joins the same merge when the planner or the reflection
node asks for it.

## Alternatives considered

- **A single vector store** — the code demonstrates the rejection rather than stating it: BM25 and graph
  retrieval were both built and wired in, which is only worth the cost if one retriever was insufficient.
- **Reciprocal-rank-fusion style score blending** instead of a reranker — TODO: not documented. The chosen
  path is notable because the retrievers' scores are *deliberately not* blended; the aggregator's ordering
  is only a pre-filter, and the cross-encoder is the sole arbiter of the final five.
- **Weighting or tuning one retriever harder** — TODO: no evidence either way.

## Consequences

**Makes easy**

- Recall is robust to the query's phrasing: an exact identifier is caught by BM25, a paraphrase by the
  vector store, an entity relationship by the graph.
- Adding a fourth retriever is additive — implement the same store surface, append its list before the
  aggregator.
- The reranker gives one comparable scale (`rerank_score`) across sources with wildly different score
  semantics.

**Makes hard / watch out for**

- **Every query pays for three searches**, and the cross-encoder scores up to ~25 candidates per pass —
  and the whole thing repeats on a reflection retry.
- **`score` is not comparable across sources.** Cosine similarity (≈0–1), raw BM25 (unbounded), and graph
  traversal weights all share one field; only `rerank_score` is meaningful.
- **`rerank_score` can be negative**, and the reflection node's escalation heuristic depends on that sign —
  swapping the reranker model for one with a different score range would silently break escalation.
- **Graph retrieval is regex-driven and silently empty** for lowercase natural-language queries with no
  proper noun, acronym, or camelCase term.
- **Three stores must be kept consistent.** Every ingest and delete must touch all three, which is why
  those operations are open-coded three times in `app.py`.
- **BM25 rebuilds its whole index on every upload**, making ingestion cost O(total corpus).
