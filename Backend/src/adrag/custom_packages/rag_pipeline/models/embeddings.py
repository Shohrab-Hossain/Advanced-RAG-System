"""
Embeddings
----------
Singleton SentenceTransformer encoder shared across the pipeline.
Avoids reloading the model on every request.
"""

import os
from sentence_transformers import SentenceTransformer

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

_embedder: SentenceTransformer | None = None


def get_embedder() -> SentenceTransformer:
    """Return (or lazily initialise) the shared embedding model."""
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(EMBEDDING_MODEL)
    return _embedder
