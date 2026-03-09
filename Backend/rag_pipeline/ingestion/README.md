# ingestion/ — Document Loading and Knowledge Base Management

Handles everything between "user uploads a file" and "chunks are ready to index".

## Files

### `loader.py` — Document Loader & Chunker
Supports: **PDF**, **DOCX**, **TXT**, **Markdown**

**`load_file(file_path)`** → `(texts, metadatas)`

Pipeline:
1. Select loader by file extension (`PyPDFLoader`, `Docx2txtLoader`, `TextLoader`, `UnstructuredMarkdownLoader`)
2. Split with `RecursiveCharacterTextSplitter` (chunk_size=500, overlap=50)
3. Attach metadata to every chunk:

```python
{
  "file_name": "report.pdf",
  "file_hash": "md5...",    # stable ID for dedup
  "chunk_index": 3,
  "total_chunks": 42,
  "source_type": "pdf",
  "page": 7,                # PDF only
}
```

**`generate_chunk_ids(file_hash, count)`** → deterministic IDs like `{hash}_{i}`
Used by ChromaDB for upsert deduplication — re-uploading the same file
updates existing chunks rather than creating duplicates.

Chunk size and overlap are configurable via `CHUNK_SIZE` and `CHUNK_OVERLAP` env vars.

---

### `registry.py` — Knowledge Base Registry
Tracks each uploaded file as a named knowledge base with per-file stats.
Persisted to `data/kb_registry.json` so it survives server restarts.

**`register(file_hash, file_name, stats)`** — add/update entry
**`list_all()`** — return all KBs sorted newest first
**`remove(file_hash)`** — delete one entry
**`clear_all()`** — wipe the registry (called on global clear)

Each entry:
```json
{
  "id": "md5hash...",
  "name": "report.pdf",
  "uploaded_at": "2025-01-01T12:00:00+00:00",
  "chunks": 42,
  "vectors": 42,
  "entities": 87,
  "edges": 134
}
```
Used by: `app.py` (`/api/knowledge-bases` endpoint, `/api/upload`).
