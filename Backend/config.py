"""
Application Configuration
--------------------------
All settings read from environment variables (with sensible defaults).
Copy .env.example → .env and fill in your OPENAI_API_KEY.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # ── LLM — OpenAI ─────────────────────────────────────────────────────────
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")

    # ── LLM — Ollama (local) ─────────────────────────────────────────────────
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2:latest")

    # ── Default provider ("openai" | "ollama") ───────────────────────────────
    DEFAULT_PROVIDER: str = os.getenv("DEFAULT_PROVIDER", "openai")

    # ── Embeddings & Reranking ────────────────────────────────────────────────
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    RERANKER_MODEL: str = os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")

    # ── Retrieval knobs ───────────────────────────────────────────────────────
    RETRIEVAL_TOP_K: int = int(os.getenv("RETRIEVAL_TOP_K", "10"))
    RERANK_TOP_K: int = int(os.getenv("RERANK_TOP_K", "5"))
    MAX_CONTEXT_CHARS: int = int(os.getenv("MAX_CONTEXT_CHARS", "4000"))
    MAX_REFLECTION_RETRIES: int = int(os.getenv("MAX_REFLECTION_RETRIES", "2"))

    # ── Chunking ──────────────────────────────────────────────────────────────
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "500"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "50"))

    # ── Storage paths ─────────────────────────────────────────────────────────
    UPLOAD_FOLDER: str = os.getenv("UPLOAD_FOLDER", "./data/uploads")
    CHROMA_PATH: str = os.getenv("CHROMA_PATH", "./data/chroma_db")
    GRAPH_PATH: str = os.getenv("GRAPH_PATH", "./data/graph_store.pkl")
    BM25_PATH: str = os.getenv("BM25_PATH", "./data/bm25_store.pkl")

    # ── Flask / CORS ──────────────────────────────────────────────────────────
    MAX_CONTENT_LENGTH: int = 50 * 1024 * 1024   # 50 MB
    ALLOWED_EXTENSIONS: set = {"pdf", "txt", "md", "docx"}
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")
    DEBUG: bool = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    PORT: int = int(os.getenv("PORT", "5000"))
