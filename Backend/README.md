# adRAG — Backend

Flask REST + SSE API over a LangGraph multi-stage RAG pipeline. Handles document ingestion, three-store hybrid retrieval (vector + BM25 + graph), LLM reasoning, and real-time streaming progress events.

## Quick Start

```bash
cd Backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # add OPENAI_API_KEY
python src/main.py               # API → http://localhost:5000
```

## Stack

- **Flask** + Flask-CORS — REST API + SSE streaming
- **LangGraph** — Pipeline state machine
- **LangChain** — LLM abstraction (OpenAI + Ollama)
- **ChromaDB** — Dense vector store
- **rank-bm25** — Sparse keyword retrieval
- **NetworkX** — Knowledge graph (GraphRAG)
- **SentenceTransformers** — Embeddings + cross-encoder reranking

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | — | Required for OpenAI provider |
| `LLM_MODEL` | `gpt-4o-mini` | OpenAI model |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server |
| `OLLAMA_MODEL` | `llama3.2` | Default Ollama model |
| `DEFAULT_PROVIDER` | `openai` | `openai` or `ollama` |
| `PORT` | `5000` | Server port |

See [`documentation/architecture.md`](documentation/architecture.md) for the full config reference.

## Documentation

Detailed docs in [`documentation/`](documentation/):

| File | Contents |
|---|---|
| [documentation/README.md](documentation/README.md) | Setup, project structure |
| [documentation/rag-pipeline.md](documentation/rag-pipeline.md) | Every pipeline node, retrieval stores, retry loop |
| [documentation/api.md](documentation/api.md) | All API endpoints + SSE event reference |
| [documentation/architecture.md](documentation/architecture.md) | Config reference, persistence, ingestion, LLM layer |
