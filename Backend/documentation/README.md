# adRAG — Backend

The backend is a Python/Flask application that exposes a REST + Server-Sent Events (SSE) API over a multi-stage LangGraph RAG pipeline. It handles document ingestion, three-store hybrid retrieval, LLM-based reasoning, and streaming real-time progress events to the frontend.

---

## Table of Contents

- [Setup & Run](#setup--run)
- [Project Structure](#project-structure)
- [Detailed Documentation](#detailed-documentation)

---

## Setup & Run

### Prerequisites

- Python 3.10+
- An OpenAI API key **or** a running [Ollama](https://ollama.com) instance

### Install

```bash
cd Backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Configure

```bash
cp .env.example .env
# Edit .env and set at minimum:
#   OPENAI_API_KEY=sk-...
```

All configuration is environment-driven. See the full reference in [architecture.md](architecture.md#configuration-reference).

### Run

```bash
# Development
python src/main.py

# Production (gunicorn — single worker required for SSE)
gunicorn -w 1 --bind 0.0.0.0:5000 --chdir src main:app
```

The API will be available at `http://localhost:5000`.

---

## Project Structure

```
Backend/
├── src/
│   ├── main.py                        # Entry point
│   ├── app.py                         # Flask app factory + all routes
│   ├── config.py                      # Environment-based configuration
│   └── rag_pipeline/
│       ├── state.py                   # RAGState TypedDict (shared pipeline state)
│       ├── graph.py                   # LangGraph workflow builder (rag_graph singleton)
│       ├── core/
│       │   └── events.py              # SSE event bus (session queues + emit())
│       ├── encoding/
│       │   ├── llm.py                 # LLM factory (OpenAI + Ollama, cached)
│       │   └── embeddings.py          # SentenceTransformer singleton
│       ├── ingestion/
│       │   ├── loader.py              # File loader + chunker (PDF/DOCX/TXT/MD)
│       │   └── registry.py            # Knowledge base registry (JSON persistence)
│       ├── retrieval/
│       │   ├── node.py                # Hybrid retrieval node (vector + BM25 + graph)
│       │   ├── web_node.py            # DuckDuckGo web search node
│       │   ├── vector/
│       │   │   └── vector_store.py    # ChromaDB (or FAISS) dense vector store
│       │   ├── keyword/
│       │   │   └── bm25_store.py      # BM25 sparse keyword store
│       │   └── graph/
│       │       └── graph_store.py     # NetworkX knowledge graph store
│       ├── ranking/
│       │   ├── aggregator.py          # Merge + deduplicate evidence
│       │   └── reranker.py            # Cross-encoder reranker (ms-marco-MiniLM)
│       └── generation/
│           ├── planner.py             # Self-RAG decision node
│           ├── compressor.py          # LLM context compressor
│           ├── reasoning.py           # Answer generator with citations
│           └── reflection.py          # Self-reflection + retry orchestration
├── data/
│   ├── uploads/                       # Uploaded source files (gitignored)
│   └── databases/                     # All persistent store data (gitignored)
│       ├── vector_db/chroma_db/
│       ├── keyword_db/bm25_store/
│       └── graph_db/graph_store/
├── .env.example
└── requirements.txt
```

---

## Detailed Documentation

| Document | Contents |
|---|---|
| [rag-pipeline.md](rag-pipeline.md) | How the RAG pipeline works: every node, the state machine, retry logic, retrieval stores |
| [api.md](api.md) | All HTTP endpoints, request/response shapes, SSE event reference |
| [architecture.md](architecture.md) | Configuration reference, data persistence, ingestion, events/SSE system |
