# rag_pipeline — Advanced RAG Package

Self-RAG pipeline built with LangGraph. Every query flows through 8 sequential nodes,
each emitting real-time SSE events to the browser.

## Package Layout

> **Note:** earlier versions exposed `bm25.py`, `vector.py` and `graph.py`
> directly under `rag_pipeline/retrieval`. Those files were simple shims and have
> now been removed; import from the appropriate subpackage (e.g. `
> rag_pipeline.retrieval.vector.vector_store`).


```
rag_pipeline/
├── graph.py          LangGraph workflow — wires all nodes together
├── state.py          RAGState TypedDict — shared data flowing between nodes
│
├── core/             Shared infrastructure
│   └── events.py     SSE event bus (per-session queues)
│
├── encoding/         Model initialisation
│   ├── embeddings.py Shared SentenceTransformer singleton
│   └── llm.py        LLM factory (ChatOpenAI / ChatOllama) + JSON helpers
│
├── ingestion/        Document loading and KB management
│   ├── loader.py     File → chunks (PDF, DOCX, TXT, Markdown)
│   └── registry.py   Knowledge-base registry (JSON persistence)
│
├── retrieval/        Finding relevant documents
│   ├── vector/        Dense vector retrieval
│   │   ├── __init__.py  exports `vector_store` (Chroma/FAISS)
│   │   └── vector_store.py     implementation (Chroma + optional FAISS)
│   ├── keyword/       Sparse keyword retrieval (BM25)
│   │   ├── __init__.py  exports `bm25_store`
│   │   └── store.py     BM25 implementation
│   ├── graph/         GraphRAG retrieval
│   │   ├── __init__.py  exports `graph_store`
│   │   └── store.py     NetworkX-based graph logic
│   ├── node.py       Hybrid retrieval pipeline node
│   └── web_node.py   Web search node (DuckDuckGo)
│
├── ranking/          Scoring and selecting the best evidence
│   ├── aggregator.py Deduplication + merge across retrieval sources
│   └── reranker.py   Cross-encoder reranking (ms-marco-MiniLM)
│
└── generation/       LLM-based text generation
    ├── planner.py    Self-RAG planner — retrieval strategy decision
    ├── compressor.py Context compression (trim to LLM window)
    ├── reasoning.py  Answer generation with inline citations
    └── reflection.py Self-reflection — grounding verification + retry
```

## Pipeline Flow

```
                         ┌─────────┐
              query ───► │ planner │  (Self-RAG: retrieve? web search? query type?)
                         └────┬────┘
               ┌──────────────┼─────────────────┐
           retrieve        web only           direct
               │               │                 │
          ┌────▼────┐    ┌──────▼──────┐         │
          │retrieval│    │ web_node    │         │
          │ (×3 KB) │    │ (DuckDuckGo)│         │
          └────┬────┘    └──────┬──────┘         │
               └────────────────┘                 │
                        │                         │
               ┌────────▼────────┐                │
               │   aggregator    │ ◄──────────────┘
               │ (dedup + merge) │
               └────────┬────────┘
                        │
               ┌────────▼────────┐
               │    reranker     │  cross-encoder scores every (q, doc) pair
               └────────┬────────┘
                        │
               ┌────────▼────────┐
               │   compressor    │  LLM compression if context > 4000 chars
               └────────┬────────┘
                        │
               ┌────────▼────────┐
               │    reasoning    │  generates cited answer as JSON
               └────────┬────────┘
                        │
               ┌────────▼────────┐
               │   reflection    │  verifies grounding
               └────────┬────────┘
          ┌─────────────┼──────────────────────────┐
     grounded        retry (KB)           retry + web escalation
          │               │                        │
         END        back to retrieval      back to retrieval
                                           (use_external=True)
```

## SSE Event Types

All nodes push typed events to the browser in real time:

| Event | Emitted by | Payload fields |
|-------|-----------|----------------|
| `stage_start` | every node | `stage`, `message` |
| `stage_complete` | every node | `stage`, `message`, node-specific data |
| `stage_skip` | retrieval, web_node | `stage`, `message` |
| `stage_error` | every node | `stage`, `error` |
| `retrieval_result` | retrieval node | `vector_count`, `bm25_count`, `graph_count` |
| `retry` | reflection node | `attempt`, `max_attempts`, `escalate_external` |
| `finalize` | reflection node | `grounded`, `message` |
| `done` | Flask route | `answer`, `sources`, `metadata` |

## State Fields (`RAGState`)

See [state.py](state.py) for the full TypedDict. Key fields:

| Field | Set by | Used by |
|-------|--------|---------|
| `query` | Flask route | all nodes |
| `provider` | Flask route | planner, compressor, reasoning, reflection |
| `retrieve` / `use_external` | planner | graph routing |
| `vector_docs` / `bm25_docs` / `graph_docs` / `web_docs` | retrieval nodes | aggregator |
| `all_docs` | aggregator | reranker |
| `context` | reranker | compressor, reasoning, reflection |
| `compressed_context` | compressor | reasoning |
| `answer` / `sources` | reasoning | reflection |
| `final_answer` / `final_sources` | reflection | Flask route |
| `pipeline_metadata` | reflection | Flask route |
