# 🗄️ Data

adRAG has no relational database and no migration system. Its data model is four things: the chunk record
that lives in three stores at once, the JSON knowledge-base registry, the in-flight pipeline state, and
the browser's `localStorage` keys.

<br>

---

<br>

## Index

| Entity | Holds |
|---|---|
| [`document-chunk/`](document-chunk/README.md) | The chunk + its metadata, its id scheme, and how it is represented in each of the three stores |
| [`kb-registry/`](kb-registry/README.md) | `kb_registry.json` — the per-file entry, its fields, and its concurrency model |
| [`rag-state/`](rag-state/README.md) | `RAGState` and `Document` — the TypedDicts that flow through the pipeline |

<br>

---

<br>

## Storage at a glance

| What | Where | Format |
|---|---|---|
| Uploaded files | `UPLOAD_FOLDER` (default `./data/uploads`) | original bytes, `secure_filename`d |
| Vector index | `CHROMA_PATH` (default `./data/databases/vector_db/chroma_db`) | Chroma `PersistentClient` files |
| FAISS index (opt-in) | `FAISS_PATH` + `<FAISS_PATH>.idx` | pickle + FAISS index file |
| BM25 corpus | `BM25_PATH` (default `./data/databases/keyword_db/bm25_store/bm25_store.pkl`) | pickle of `{corpus, metadatas}` |
| Entity graph | `GRAPH_PATH` (default `./data/databases/graph_db/graph_store/graph_store.pkl`) | pickle of `{graph, doc_store}` |
| KB registry | `KB_REGISTRY_PATH` (default `<DATABASE_ROOT>/kb_registry.json`) | JSON object keyed by `file_hash` |
| Chat history | browser `localStorage["rag-chat-history"]` | JSON array, newest first, max 50 |
| Theme | browser `localStorage["rag-theme"]` | `"dark"` \| `"light"` |

Every `./data/…` default is resolved against the **process working directory** (`config.py:44`), not the
repository root — so the tree lands under whatever directory the backend was started in. In practice that
is `Backend/src/data/`.

> [!NOTE]
> **This runtime state is ignored at both possible locations.** `.gitignore:32` covers `Backend/src/data/`
> — the real one — and `.gitignore:33` covers `Backend/data/`, for the case where someone starts the
> process one level up; the reasoning is recorded in a comment at `.gitignore:29-31`. Nothing under either
> path is tracked (`git check-ignore -v` on the Chroma database resolves to `.gitignore:32`). Keep both
> entries: dropping the first silently commits a growing vector database. See
> [`../operations/configuration/README.md`](../operations/configuration/README.md).

<br>

## Migrations

There is no migration framework. Two implicit compatibility behaviours exist:

- `ingestion/registry.py` moves a legacy `./data/kb_registry.json` to `KB_REGISTRY_PATH` on import if the
  new path does not yet exist.
- Every pickle load is wrapped in a bare `except` that resets to an empty store — so an incompatible
  pickle silently wipes that store rather than crashing the process.

Changing `EMBEDDING_MODEL` or the chunking parameters invalidates the existing index semantically without
any error: the safe move is to clear and re-upload everything.
