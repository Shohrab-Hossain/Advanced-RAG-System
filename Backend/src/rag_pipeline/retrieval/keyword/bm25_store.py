"""
BM25 Store
-----------
Sparse keyword retrieval using rank-bm25 (BM25Okapi).
Corpus and metadata are pickled to disk for persistence across restarts.
"""

import os
import pickle
import re
from typing import List, Optional

from rank_bm25 import BM25Okapi

from config import Config

BM25_PATH = os.getenv("BM25_PATH", Config.BM25_PATH)


class BM25Store:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        os.makedirs(os.path.dirname(BM25_PATH), exist_ok=True)
        self.corpus: List[str] = []
        self.metadatas: List[dict] = []
        self.bm25: Optional[BM25Okapi] = None
        self._load()
        self._initialized = True

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r"\b\w+\b", text.lower())

    def _rebuild(self) -> None:
        if self.corpus:
            tokenized = [self._tokenize(t) for t in self.corpus]
            self.bm25 = BM25Okapi(tokenized)

    def _save(self) -> None:
        with open(BM25_PATH, "wb") as f:
            pickle.dump({"corpus": self.corpus, "metadatas": self.metadatas}, f)

    def _load(self) -> None:
        if os.path.exists(BM25_PATH):
            try:
                with open(BM25_PATH, "rb") as f:
                    data = pickle.load(f)
                    self.corpus = data["corpus"]
                    self.metadatas = data["metadatas"]
                    self._rebuild()
            except Exception:
                self.corpus = []
                self.metadatas = []

    # ── Public API ────────────────────────────────────────────────────────────

    def add_documents(self, texts: List[str], metadatas: List[dict]) -> None:
        self.corpus.extend(texts)
        self.metadatas.extend(metadatas)
        self._rebuild()
        self._save()

    def search(self, query: str, top_k: int = 10) -> List[dict]:
        if not self.corpus or self.bm25 is None:
            return []
        scores = self.bm25.get_scores(self._tokenize(query))
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        results = []
        for idx in top_indices:
            if scores[idx] > 0:
                results.append({
                    "content": self.corpus[idx],
                    "metadata": self.metadatas[idx],
                    "score": float(scores[idx]),
                    "source": "bm25",
                    "rerank_score": 0.0,
                })
        return results

    def delete_by_file(self, file_hash: str) -> int:
        """Remove all chunks from a specific file. Returns count removed."""
        kept = [(t, m) for t, m in zip(self.corpus, self.metadatas)
                if m.get("file_hash") != file_hash]
        removed = len(self.corpus) - len(kept)
        if kept:
            self.corpus, self.metadatas = map(list, zip(*kept))
        else:
            self.corpus, self.metadatas = [], []
        self.bm25 = None
        self._rebuild()
        self._save()
        return removed

    def count(self) -> int:
        return len(self.corpus)

    def clear(self) -> None:
        self.corpus = []
        self.metadatas = []
        self.bm25 = None
        self._save()


bm25_store = BM25Store()
