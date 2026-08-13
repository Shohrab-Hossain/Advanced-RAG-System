# Entity: Document chunk

The unit of indexing and retrieval. Produced by `load_file()` in
`Backend/src/rag_pipeline/ingestion/loader.py` and written into all three stores.

<br>

## Identity and shape

| Field | Type | Constraints |
|---|---|---|
| chunk id | string | `f"{file_hash}_{i}"`, `i` zero-based. Deterministic — `generate_chunk_ids()`. Used as the Chroma id and the graph document-node id. |
| text | string | ~`CHUNK_SIZE` (500) characters with `CHUNK_OVERLAP` (50) overlap; split by `RecursiveCharacterTextSplitter` with separators `["\n\n", "\n", ".", " ", ""]`. |

## Metadata (one dict per chunk)

| Field | Type | Notes |
|---|---|---|
| `file_name` | string | `Path(file_path).name` |
| `file_path` | string | absolute path where the upload was saved |
| `file_hash` | string | **MD5 of the file's bytes** — the document's identity across all stores |
| `chunk_index` | int | 0-based position within the document |
| `total_chunks` | int | number of chunks the document produced |
| `source_type` | string | `"pdf"` \| `"text"` \| `"markdown"` \| `"docx"` (from `SUPPORTED_EXTENSIONS`), or `"unknown"` |
| `page` | int | **present only when the loader supplied one** (PDF); cast with `int()` |

Web results (from `retrieval/web_node.py`) reuse the same `Document` shape but a different metadata set:
`{url, title, source_type: "web", file_name: <href>}`.

<br>

## Representation per store

| Store | How the chunk is stored |
|---|---|
| **Chroma** | One record in collection `rag_documents`: `id = <file_hash>_<i>`, `document = text`, `metadata` as above, `embedding` from `SentenceTransformer.encode`. Collection metadata `{"hnsw:space": "cosine"}`. |
| **FAISS** (opt-in) | A normalised float32 row in an `IndexFlatIP`, with `ids`, `documents`, and `metadatas` held as parallel Python lists and pickled alongside. Position in the lists is the index row. |
| **BM25** | `corpus[i] = text` and `metadatas[i] = metadata`, parallel lists. The `BM25Okapi` object is built over `re.findall(r"\b\w+\b", text.lower())` tokens and is **rebuilt**, not persisted. |
| **Graph** | A node keyed by the chunk id with `{type: "document", content_preview: text[:200], metadata}`, plus `doc_store[chunk_id] = {content, metadata}` holding the full text. Edges connect it to `entity:<name>` nodes with an integer `weight`. |

Note the graph deliberately keeps the full text in `doc_store` rather than on the node — the node carries
only a 200-character preview.

<br>

## Retrieved form

Every retriever returns the same `Document` TypedDict (`state.py`):

```python
{ "content": str, "metadata": dict, "score": float,
  "source": "vector" | "bm25" | "graph" | "web", "rerank_score": float }
```

`score` is retriever-native (cosine similarity, raw BM25, graph traversal weight, or a fixed `0.7` for
web). `rerank_score` is `0.0` until the reranker sets it and **may be negative**.

<br>

## Lifecycle

- **Created** on upload, after any prior chunks with the same `file_hash` are deleted from all three
  stores.
- **Never updated in place** — a document is replaced wholesale by re-uploading.
- **Deleted** by `file_hash` via `delete_by_file()` on each store; the graph additionally prunes entity
  nodes left with degree 0.

<br>

## Constraints worth knowing

- **`file_hash` is content-addressed, `file_name` is not.** Two identical files uploaded under different
  names produce different `UPLOAD_FOLDER` paths but the *same* hash, so the second replaces the first's
  index entries while both files remain on disk.
- **Chroma metadata values must be scalars.** All fields above are strings or ints, which is why `page` is
  coerced with `int()`.
- **Chunk boundaries are character-based**, not token-based — a 500-character chunk is roughly 100–150
  tokens depending on content.
