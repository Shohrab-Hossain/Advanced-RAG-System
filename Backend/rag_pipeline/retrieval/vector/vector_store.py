"""
Moved from retrieval/vector.py; contains both Chroma and FAISS implementations.
"""

import os
import uuid
import pickle
from typing import List, Optional

from config import Config
from ...encoding.embeddings import get_embedder

# Determine which backend to use
BACKEND = Config.VECTOR_BACKEND

# ensure root dirs exist
os.makedirs(Config.VECTOR_ROOT, exist_ok=True)

# legacy migration: if user previously used './data/chroma_db' move it
if BACKEND == 'chroma':
    legacy = './data/chroma_db'
    if os.path.exists(legacy) and not os.path.exists(Config.CHROMA_PATH):
        os.makedirs(os.path.dirname(Config.CHROMA_PATH), exist_ok=True)
        import shutil
        shutil.move(legacy, Config.CHROMA_PATH)
        # clean up empty old directory
        try:
            if os.path.isdir(legacy) and not os.listdir(legacy):
                os.rmdir(legacy)
        except Exception:
            pass

# chroma constants
COLLECTION_NAME = "rag_documents"

# faiss imports deferred to avoid dependency when not used
if BACKEND == 'faiss':
    try:
        import faiss
        import numpy as np
    except ImportError:
        raise RuntimeError("VECTOR_BACKEND=faiss requires faiss-cpu to be installed")


class _BaseVectorStore:
    @property
    def embedder(self):
        return get_embedder()


# existing Chroma implementation
class ChromaVectorStore(_BaseVectorStore):
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        os.makedirs(Config.CHROMA_PATH, exist_ok=True)
        import chromadb
        self.client = chromadb.PersistentClient(path=Config.CHROMA_PATH)
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        self._initialized = True

    def add_documents(
        self,
        texts: List[str],
        metadatas: List[dict],
        ids: Optional[List[str]] = None,
    ) -> None:
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


# minimal FAISS implementation for those who prefer it
class FaissVectorStore(_BaseVectorStore):
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        # path where index+metadata will be stored
        self.index_path = Config.FAISS_PATH
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        self.ids: List[str] = []
        self.documents: List[str] = []
        self.metadatas: List[dict] = []
        self.dim = None
        self.index = None
        self._load()
        self._initialized = True

    def _load(self):
        if os.path.exists(self.index_path):
            try:
                with open(self.index_path, "rb") as f:
                    data = pickle.load(f)
                self.ids = data.get("ids", [])
                self.documents = data.get("documents", [])
                self.metadatas = data.get("metadatas", [])
                self.index = faiss.read_index(data["index_file"])
                self.dim = self.index.d
            except Exception:
                # start fresh
                self.ids = []
                self.documents = []
                self.metadatas = []
                self.index = None
                self.dim = None
        else:
            self.index = None

    def _save(self):
        # write index to a temporary file and store bytes reference
        idx_file = self.index_path + ".idx"
        if self.index is not None:
            faiss.write_index(self.index, idx_file)
        with open(self.index_path, "wb") as f:
            pickle.dump({
                "ids": self.ids,
                "documents": self.documents,
                "metadatas": self.metadatas,
                "index_file": idx_file,
            }, f)

    def _ensure_index(self, emb_vec):
        if self.index is None:
            self.dim = len(emb_vec)
            # use inner product on normalized vectors for cosine
            self.index = faiss.IndexFlatIP(self.dim)

    def add_documents(
        self,
        texts: List[str],
        metadatas: List[dict],
        ids: Optional[List[str]] = None,
    ) -> None:
        if not texts:
            return
        embs = self.embedder.encode(texts).astype("float32")
        faiss.normalize_L2(embs)
        self._ensure_index(embs.shape[1])
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in texts]
        self.index.add(embs)
        self.ids.extend(ids)
        self.documents.extend(texts)
        self.metadatas.extend(metadatas)
        self._save()

    def search(self, query: str, top_k: int = 10) -> List[dict]:
        if self.index is None or self.index.ntotal == 0:
            return []
        qemb = self.embedder.encode([query]).astype("float32")
        faiss.normalize_L2(qemb)
        D, I = self.index.search(qemb, min(top_k, self.index.ntotal))
        docs = []
        for i, idx in enumerate(I[0]):
            if idx < 0 or idx >= len(self.documents):
                continue
            docs.append({
                "content": self.documents[idx],
                "metadata": self.metadatas[idx],
                "score": float(D[0][i]),
                "source": "vector",
                "rerank_score": 0.0,
            })
        return docs

    def delete_by_file(self, file_hash: str) -> int:
        kept = []
        removed = 0
        for i, m in enumerate(self.metadatas):
            if m.get("file_hash") == file_hash:
                removed += 1
            else:
                kept.append((self.ids[i], self.documents[i], m))
        if removed == 0:
            return 0
        self.ids, self.documents, self.metadatas = map(list, zip(*kept))
        # rebuild faiss index
        if self.ids:
            embs = self.embedder.encode(self.documents).astype("float32")
            faiss.normalize_L2(embs)
            self.index = faiss.IndexFlatIP(embs.shape[1])
            self.index.add(embs)
        else:
            self.index = None
        self._save()
        return removed

    def count(self) -> int:
        return len(self.ids)

    def clear(self) -> None:
        self.ids = []
        self.documents = []
        self.metadatas = []
        self.index = None
        self._save()


# choose appropriate store class
if BACKEND == 'faiss':
    vector_store = FaissVectorStore()
else:
    vector_store = ChromaVectorStore()
