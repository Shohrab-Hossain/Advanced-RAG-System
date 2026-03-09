# retrieval/ — Finding Relevant Documents

Three complementary retrieval strategies run in parallel, each capturing different
kinds of relevance. Results are forwarded to `ranking/` for scoring.

## Files

### `vector.py` — Dense Semantic Search
**Store:** ChromaDB (persistent on disk)
**Model:** `all-MiniLM-L6-v2` via `encoding/embeddings.py` singleton
**How it works:** Encodes query and documents as embedding vectors; ranks by cosine similarity.
**Best for:** Paraphrase matches, semantic similarity ("how does X work?" finds docs about X even without the exact words).

Key methods:
- `add_documents(texts, metadatas, ids)` — encode and upsert chunks
- `search(query, top_k)` → scored doc list
- `delete_by_file(file_hash)` → removes a specific KB's chunks
- `count()` → total indexed chunks

---

### `bm25.py` — Sparse Keyword Search
**Store:** In-memory `rank-bm25`, pickled to disk
**How it works:** TF-IDF style term frequency scoring; no neural models needed.
**Best for:** Exact keyword matches, technical jargon, proper nouns, acronyms.

Key methods:
- `add_documents(texts, metadatas)` — extend corpus and rebuild index
- `search(query, top_k)` → scored doc list
- `delete_by_file(file_hash)` → filters corpus and rebuilds
- `count()` → corpus size

---

### `graph.py` — GraphRAG Entity Traversal
**Store:** NetworkX graph, pickled to disk
**How it works:** Extracts named entities (proper nouns, acronyms, camelCase) from documents and builds a bipartite graph (doc ↔ entity). Query entities are matched and 2-hop document neighbours are returned.
**Best for:** Relationship queries, "what does X say about Y", entity co-occurrence.

Graph schema:
```
[document node] ──── [entity node]
                 weight = co-occurrence count
```

Key methods:
- `add_document(doc_id, content, metadata)` — extract entities and add edges
- `search(query, top_k)` → scored doc list (2-hop traversal)
- `delete_by_file(file_hash)` → remove doc nodes + orphaned entity nodes
- `count_entities_by_file(file_hash)` → per-KB entity count
- `get_stats()` → `{documents, entities, edges}`

---

### `node.py` — Hybrid Retrieval Pipeline Node
LangGraph node that calls all three stores and returns:
```python
{"vector_docs": [...], "bm25_docs": [...], "graph_docs": [...]}
```
Skips all retrieval if `state["retrieve"] == False` (planner decision).
Controlled by `RETRIEVAL_TOP_K` env var (default: 10).

---

### `web_node.py` — Web Search Node
LangGraph node that calls DuckDuckGo when `state["use_external"] == True`.
This flag is set by either:
1. The planner (for live data / recent events queries)
2. The reflection node (escalation when KB had no relevant content)

Returns `{"web_docs": [...]}` or `{"web_docs": []}` (graceful skip/error).

## Data Flow

```
query
  ├── vector.py  →  vector_docs  (dense, semantic)
  ├── bm25.py    →  bm25_docs    (sparse, keyword)
  ├── graph.py   →  graph_docs   (entity graph)
  └── web_node.py → web_docs    (live web, optional)
           │
           ▼
      aggregator (ranking/)
```
