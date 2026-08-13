# Feature: Hybrid retrieval

**Purpose:** raise recall by querying three retrievers with different failure modes for every question,
then letting a cross-encoder decide what actually matters.

**Entry point:** `retrieval_node(state)` in `Backend/src/rag_pipeline/retrieval/node.py`, called by the
graph after the planner sets `retrieve=True`.

**Implemented in:**

| Retriever | File | Library | `source` tag |
|---|---|---|---|
| Dense vector | `retrieval/vector/vector_store.py` | `chromadb` (default) or `faiss` | `"vector"` |
| Sparse keyword | `retrieval/keyword/bm25_store.py` | `rank_bm25.BM25Okapi` | `"bm25"` |
| Entity graph | `retrieval/graph/graph_store.py` | `networkx` | `"graph"` |
| Web (optional) | `retrieval/web_node.py` | `ddgs` (DuckDuckGo) | `"web"` |

Embeddings come from the shared singleton in `encoding/embeddings.py`
(`all-MiniLM-L6-v2` by default).

**Inputs:** the raw query string plus `RETRIEVAL_TOP_K` (default 10).
**Outputs:** three separate lists on the state — `vector_docs`, `bm25_docs`, `graph_docs` — each a list of
`Document` dicts `{content, metadata, score, source, rerank_score}`. `web_docs` is filled separately by the
external-tools node.

**Behaviour per retriever:**

- **Vector.** Embeds the query, queries Chroma's `rag_documents` collection with
  `n_results=min(top_k, collection.count())`, and converts distance to similarity as `1.0 - distance`
  (collection metadata `hnsw:space: cosine`). Returns `[]` immediately when the collection is empty.
- **BM25.** Tokenises with `re.findall(r"\b\w+\b", text.lower())` — the same tokenizer for corpus and
  query — scores the whole corpus, takes the top-k indices, and **drops any result with `score <= 0`**, so
  a query sharing no terms with the corpus returns nothing.
- **Graph.** Extracts entities from the *query* with the same regexes used at ingestion. For each entity
  node found: 1-hop document neighbours score `edge_weight × 2.0`; 2-hop paths (entity → document →
  entity → document) add `0.5` each. Returns `[]` when the query contains no recognisable entity — which is
  common for lowercase natural-language questions. Uses `top_k = max(RETRIEVAL_TOP_K // 2, 3)` → 5.
- **Web.** Only when `use_external`. `DDGS().text(query, max_results=5)`; each hit becomes a document with
  a fixed `score: 0.7` and metadata `{url, title, source_type: "web", file_name: <href>}`. Imports `ddgs`
  first and falls back to the legacy `duckduckgo_search` module name.

**Merging.** `aggregator_node` concatenates all four lists, deduplicates by MD5 of `content` keeping the
highest `score`, and sorts descending. `reranker_node` then rescores every surviving pair with
`cross-encoder/ms-marco-MiniLM-L-6-v2` and keeps `RERANK_TOP_K` (5).

**Depends on:** an indexed corpus ([`knowledge-base-management`](../knowledge-base-management/README.md));
the shared embedder; `Config.VECTOR_BACKEND` for which vector implementation is live.

**Gotchas:**

- **Scores are not comparable across retrievers.** Cosine similarity (≈0–1), raw BM25 (unbounded), and
  graph traversal weights all land in the same `score` field. The pre-rerank ordering is therefore
  arbitrary between sources — only `rerank_score` is meaningful, and it is the sole basis for the final
  top-5.
- **`rerank_score` can be negative.** That is not a bug; the reflection node uses `max(rerank_score) < 0`
  as its "the knowledge base had nothing useful" signal.
- **Graph retrieval is silent on ordinary questions.** No capitalised proper noun, acronym, or camelCase
  term in the query means zero graph hits.
- **The `retrieval_node` docstring claims the three run "in parallel"** — they are sequential calls in the
  current implementation.
- **Retrieval always spans the entire index.** There is no per-knowledge-base filter, even though the
  registry tracks files individually.
- **Switching `VECTOR_BACKEND` does not migrate data.** Chroma and FAISS keep separate stores; flipping the
  variable silently exposes a different (probably empty) index.
