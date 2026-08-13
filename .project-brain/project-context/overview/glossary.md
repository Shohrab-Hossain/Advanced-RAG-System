# Glossary

Domain vocabulary as this project uses it. Where a term maps to a concrete identifier in the code, the
identifier is given — these are the names to search for.

| Term | Means here |
|---|---|
| **adRAG** | The product name. Appears as the `<title>`, `application-name`, and OG/Twitter title in `Frontend/public/index.html` and as the hero `<h1>` in `HomeView.vue`. |
| **Pipeline** | The eight-node LangGraph workflow compiled in `Backend/src/rag_pipeline/graph.py`: `planner → retrieval → external_tools → aggregate → rerank → compress → reason → reflect`. |
| **Node** | One pipeline step. Implemented as a plain function `<name>_node(state: RAGState) -> dict` returning only the state keys it modifies. |
| **Stage** | The UI-facing name for a node. The frontend's `STAGES` array (`Frontend/src/stores/rag.js`) defines the eight stage ids, labels, icons, and descriptions; SSE events carry `data.stage` matching those ids. |
| **`RAGState`** | The single `TypedDict` that flows through every node (`Backend/src/rag_pipeline/state.py`). See [`../data/rag-state/README.md`](../data/rag-state/README.md). |
| **Self-RAG** | The pattern where the model itself decides whether retrieval is needed. Here it is the **planner** node, which outputs `retrieve`, `use_external`, and `query_type` as JSON. |
| **Hybrid retrieval** | Running dense (vector), sparse (BM25), and graph retrieval for the same query and merging the results. Implemented in `retrieval/node.py`. |
| **Dense / vector retrieval** | Embedding-similarity search over chunk embeddings. Default backend Chroma with cosine space; FAISS is an opt-in alternative. `source: "vector"`. |
| **Sparse / BM25 retrieval** | Okapi BM25 keyword scoring over a tokenized corpus (`rank_bm25.BM25Okapi`). `source: "bm25"`. |
| **GraphRAG** | Entity-graph retrieval. Chunks and extracted entities form a bipartite NetworkX graph; a query's entities are matched and the graph is traversed up to 2 hops to surface related chunks. `source: "graph"`. |
| **Entity** | A capitalised multi-word proper noun, an all-caps acronym (2–6 chars), or a camelCase term extracted from chunk text by regex in `graph_store._extract_entities`. Stored as a graph node keyed `entity:<lowercased name>`. |
| **External tools / web search** | The optional DuckDuckGo search node (`retrieval/web_node.py`), used when the planner sets `use_external=True` or when reflection escalates. `source: "web"`. |
| **Aggregation** | Merging the four document lists and dropping duplicates by MD5 of chunk content, keeping the highest-scoring copy (`ranking/aggregator.py`). |
| **Reranking** | Rescoring every `(query, chunk)` pair with a cross-encoder and keeping the top `RERANK_TOP_K`. Produces `rerank_score`, which unlike the retrieval `score` can be **negative** for irrelevant pairs. |
| **Compression** | LLM-driven extraction of only the query-relevant sentences from the top chunks, applied only when the concatenated text exceeds `MAX_CONTEXT_CHARS`. |
| **Grounding** | Whether every factual claim in the generated answer is traceable to the retrieved context. Judged by the reflection node, surfaced as `grounded: bool`. |
| **Reflection loop** | The conditional edge from `reflect` back to `retrieval` when the answer is not grounded and retry budget remains (`MAX_REFLECTION_RETRIES`, default 2 → 3 attempts total). |
| **Escalation** | On a retry where the knowledge base was judged insufficient, reflection sets `use_external=True` so the next pass adds web search. |
| **KB insufficient** | The heuristic that decides escalation: zero context documents, or the best `rerank_score` across the context is `< 0` (the ms-marco cross-encoder emits negative logits for irrelevant pairs). |
| **Knowledge base (KB)** | One uploaded file, tracked as a registry entry keyed by its MD5 `file_hash`, with per-file chunk/vector/entity/edge counts. Not a separate searchable partition — retrieval always spans the whole index. |
| **Chunk** | One split of a document, ~500 characters with 50 characters of overlap. Its stable id is `<file_hash>_<index>`. |
| **`file_hash`** | MD5 of the uploaded file's bytes. The identity of a document across all three stores and the registry; re-uploading the same file replaces its old entries. |
| **Session** | One query run. Identified by a UUID `session_id` that keys an in-memory `queue.Queue` used to stream that run's SSE events. |
| **SSE** | Server-Sent Events. The `/api/query` response is a `text/event-stream` of `data: {json}\n\n` frames; the frontend reads it with `fetch` + a `ReadableStream` reader (not `EventSource`, because the request is a POST). |
| **Provider** | The LLM backend for a run: `"openai"` or `"ollama"`. Chosen per request in the body and defaulted from `DEFAULT_PROVIDER`. |
| **Confidence** | A float `0.0–1.0` the reasoning and reflection prompts ask the LLM to self-report. It is a model claim, not a computed metric. |
