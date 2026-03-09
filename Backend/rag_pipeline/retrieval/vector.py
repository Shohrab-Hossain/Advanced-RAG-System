"""
Vector Store (ChromaDB)
------------------------
Dense retrieval via cosine-similarity search over document embeddings.
Uses the shared SentenceTransformer from encoding.embeddings.
Singleton so the index is shared across all requests.
"""

import os
import uuid
from typing import List, Optional

import chromadb

from ..encoding.embeddings import get_embedder

CHROMA_PATH = os.getenv("CHROMA_PATH", "./data/chroma_db")
COLLECTION_NAME = "rag_documents"


class VectorStore:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        os.makedirs(CHROMA_PATH, exist_ok=True)
        self.client = chromadb.PersistentClient(path=CHROMA_PATH)
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        self._initialized = True

    @property
    def embedder(self):
        """Lazy proxy to the shared embedding model."""
        return get_embedder()

    def add_documents(
        self,
        texts: List[str],
        metadatas: List[dict],
        ids: Optional[List[str]] = None,
    ) -> None:
        """Encode and store documents."""
        if not texts:
            return
        embeddings = self.embedder.encode(texts).tolist()
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in texts]
        self.collection.add(
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
            ids=ids,
        )

    def search(self, query: str, top_k: int = 10) -> List[dict]:
        """Return top-k documents by cosine similarity."""
        total = self.collection.count()
        if total == 0:
            return []
        query_emb = self.embedder.encode([query]).tolist()
        results = self.collection.query(
            query_embeddings=query_emb,
            n_results=min(top_k, total),
            include=["documents", "metadatas", "distances"],
        )
        docs = []
        for i, content in enumerate(results["documents"][0]):
            docs.append({
                "content": content,
                "metadata": results["metadatas"][0][i],
                "score": float(1.0 - results["distances"][0][i]),
                "source": "vector",
                "rerank_score": 0.0,
            })
        return docs

    def delete_by_file(self, file_hash: str) -> int:
        """Delete all chunks belonging to a file. Returns count removed."""
        result = self.collection.get(where={"file_hash": file_hash})
        ids = result.get("ids", [])
        if ids:
            self.collection.delete(ids=ids)
        return len(ids)

    def count(self) -> int:
        return self.collection.count()

    def clear(self) -> None:
        self.client.delete_collection(COLLECTION_NAME)
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )


vector_store = VectorStore()
