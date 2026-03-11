"""
Document Loader & Chunker
--------------------------
Loads PDF, DOCX, TXT, and Markdown files.
Splits them into overlapping chunks for indexing.
Returns (texts, metadatas) ready for all three stores.
"""

import hashlib
import os
from pathlib import Path
from typing import List, Tuple

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    Docx2txtLoader,
    UnstructuredMarkdownLoader,
)

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))

SUPPORTED_EXTENSIONS = {
    ".pdf": "pdf",
    ".txt": "text",
    ".md": "markdown",
    ".docx": "docx",
}


def _hash_file(file_path: str) -> str:
    """MD5 hash of file content — used for stable chunk IDs and dedup."""
    h = hashlib.md5()
    with open(file_path, "rb") as f:
        for block in iter(lambda: f.read(4096), b""):
            h.update(block)
    return h.hexdigest()


def _get_loader(file_path: str):
    ext = Path(file_path).suffix.lower()
    if ext == ".pdf":
        return PyPDFLoader(file_path)
    if ext == ".txt":
        return TextLoader(file_path, encoding="utf-8")
    if ext == ".md":
        return UnstructuredMarkdownLoader(file_path)
    if ext == ".docx":
        return Docx2txtLoader(file_path)
    raise ValueError(f"Unsupported file type: {ext}")


def load_file(file_path: str) -> Tuple[List[str], List[dict]]:
    """
    Load a file, split into chunks, and return:
      texts     — list of chunk strings
      metadatas — list of metadata dicts (one per chunk)
    """
    loader = _get_loader(file_path)
    raw_docs = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ".", " ", ""],
    )
    split_docs = splitter.split_documents(raw_docs)

    file_name = Path(file_path).name
    ext = Path(file_path).suffix.lower()
    file_hash = _hash_file(file_path)
    total = len(split_docs)

    texts, metadatas = [], []
    for i, doc in enumerate(split_docs):
        texts.append(doc.page_content)
        meta: dict = {
            "file_name": file_name,
            "file_path": file_path,
            "file_hash": file_hash,
            "chunk_index": i,
            "total_chunks": total,
            "source_type": SUPPORTED_EXTENSIONS.get(ext, "unknown"),
        }
        if "page" in doc.metadata:
            meta["page"] = int(doc.metadata["page"])
        metadatas.append(meta)

    return texts, metadatas


def generate_chunk_ids(file_hash: str, count: int) -> List[str]:
    """Stable, deterministic IDs for each chunk (for Chroma upsert dedup)."""
    return [f"{file_hash}_{i}" for i in range(count)]
