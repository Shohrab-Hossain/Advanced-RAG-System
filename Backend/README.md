# RAG Backend

Flask API serving an advanced Retrieval-Augmented Generation pipeline.

## Quick Start

```bash
cd Backend
pip install -r requirements.txt
cp .env.example .env          # fill in OPENAI_API_KEY (or configure Ollama)
python main.py                # starts on http://localhost:5000
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/query` | Run the RAG pipeline — returns SSE stream |
| `POST` | `/api/upload` | Upload and index a document |
| `GET` | `/api/documents` | Global index statistics |
| `GET` | `/api/knowledge-bases` | Per-file knowledge base stats |
| `DELETE` | `/api/knowledge-bases/<hash>` | Remove a specific knowledge base |
| `DELETE` | `/api/clear` | Wipe all indexed documents |
| `GET` | `/api/providers` | LLM provider availability |
| `GET` | `/api/health` | Health check |

## File Structure

```
Backend/
├── main.py               Entry point (python main.py)
├── app.py                Flask app factory, all route handlers
├── config.py             All settings (env vars + defaults)
├── requirements.txt      Python dependencies
├── .env.example          Environment variable template
└── rag_pipeline/         Core RAG package → see rag_pipeline/README.md
```

## Configuration

Copy `.env.example` to `.env` and set:

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | Required for OpenAI provider |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3.2:latest` | Local model name |
| `DEFAULT_PROVIDER` | `openai` | `openai` or `ollama` |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence-transformers model |
| `RERANKER_MODEL` | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Cross-encoder model |
| `RETRIEVAL_TOP_K` | `10` | Docs retrieved per strategy |
| `RERANK_TOP_K` | `5` | Docs kept after reranking |
| `MAX_CONTEXT_CHARS` | `4000` | Context window before compression |
| `MAX_REFLECTION_RETRIES` | `2` | Self-reflection retry budget |
| `CHUNK_SIZE` | `500` | Document chunk size (chars) |
