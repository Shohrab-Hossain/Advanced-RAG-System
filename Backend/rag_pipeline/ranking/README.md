# ranking/ — Scoring and Selecting Evidence

Takes the raw union of all retrieval results, deduplicates them, and then
re-scores every candidate with a neural cross-encoder to pick the most
relevant documents for the LLM context window.

## Files

### `aggregator.py` — Evidence Aggregator Node
**Input:** `vector_docs + bm25_docs + graph_docs + web_docs`
**Output:** `all_docs` — deduplicated, sorted by original retrieval score

Deduplication strategy: MD5 hash of document content. When the same chunk
appears in multiple retrievers (common for BM25 + vector), only the copy
with the **highest score** is kept.

```
Before: 30 raw docs (10 vector + 10 BM25 + 5 graph + 5 web)
After:  ~18 unique docs (duplicates removed, sorted by score)
```

SSE event: `stage_complete` with `before`, `after`, `sources` distribution.

---

### `reranker.py` — Cross-Encoder Reranker Node
**Model:** `cross-encoder/ms-marco-MiniLM-L-6-v2`
**Input:** `all_docs` (up to ~20 candidates)
**Output:** `context` — top-k docs by cross-encoder score

**Why cross-encoder?** The retrieval stage uses fast bi-encoder similarity
(query and doc encoded independently). The cross-encoder sees *both* the query
and document together, producing much more accurate relevance scores — but is
too slow to run on thousands of documents, so it only rescores the small
candidate set from the aggregator.

Score semantics (ms-marco logits):
- `> 5` → highly relevant (green in UI)
- `2–5` → relevant (brand colour)
- `< 0` → not relevant — triggers web search escalation in `reflection.py`

Controlled by `RERANK_TOP_K` env var (default: 5).
Falls back to original score-sort on model error.

## Data Flow

```
vector_docs ─┐
bm25_docs   ─┤  aggregator  →  all_docs  →  reranker  →  context (top-k)
graph_docs  ─┤
web_docs    ─┘
```
