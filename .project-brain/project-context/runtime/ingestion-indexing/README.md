# Runtime: ingestion and indexing

What happens between a user dropping a file and that file being queryable. Implemented in the
`/api/upload` route (`Backend/src/app.py`), `ingestion/loader.py`, `ingestion/registry.py`, and the three
store modules.

<br>

## The flow

1. **Validate.** `file` field must exist, filename must be non-empty, extension must be in
   `Config.ALLOWED_EXTENSIONS` → otherwise `400`. That set holds **35 extensions**
   (`config.py:62-65`, listed in full in
   [`../../operations/configuration/README.md`](../../operations/configuration/README.md)) — far more than
   the four suffixes the loader map below handles, so an accepted upload can still fail at step 3. Flask's
   `MAX_CONTENT_LENGTH` caps the body at **50 MB**.
2. **Save.** `secure_filename(f.filename)` then write to `Config.UPLOAD_FOLDER` (created at app start).
   **The sanitised name is the identity on disk** — uploading two different files that sanitise to the same
   name overwrites the first.
3. **Load and split.** `load_file(path)`:
   - Picks a loader by suffix — `.pdf` → `PyPDFLoader`, `.txt` → `TextLoader(encoding="utf-8")`,
     `.md` → `UnstructuredMarkdownLoader`, `.docx` → `Docx2txtLoader`. Any other suffix raises
     `ValueError`.
   - Splits with `RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP,
     separators=["\n\n", "\n", ".", " ", ""])` — defaults **500 / 50** characters.
   - Computes `file_hash` = MD5 of the file's bytes, streamed in 4096-byte blocks.
   - Returns parallel `texts` / `metadatas` lists. Every metadata dict carries `file_name`, `file_path`,
     `file_hash`, `chunk_index`, `total_chunks`, `source_type`, plus `page` (int) when the loader supplied
     one.
   - Empty extraction → the route returns `422 "No text could be extracted from this file"`.
4. **Mint ids.** `generate_chunk_ids(file_hash, n)` → `["<hash>_0", "<hash>_1", …]`. Deterministic, so the
   same file always produces the same ids.
5. **Replace, don't duplicate.** Before indexing, the route deletes any prior data for this `file_hash`
   from all three stores and the registry. Re-uploading an identical file therefore refreshes it rather
   than doubling it — the hash, not the filename, is what makes this work.
6. **Index into all three stores:**
   - `vector_store.add_documents(texts, metadatas, chunk_ids)` — embeds every chunk with the shared
     `SentenceTransformer` and adds them to the Chroma collection `rag_documents`.
   - `bm25_store.add_documents(texts, metadatas)` — extends the corpus, **rebuilds the entire BM25 index**,
     and pickles.
   - `graph_store.add_document(chunk_id, text, meta)` **per chunk** — the only per-chunk loop, because each
     chunk becomes its own graph node.
7. **Register.** `kb_registry.register(file_hash, filename, {chunks, vectors, entities, edges})` writes the
   entry and returns it. `vectors` is set equal to `chunks` (one embedding per chunk); `entities` comes from
   `graph_store.count_entities_by_file(file_hash)`; `edges` is the **global** graph edge count, not the
   file's.
8. **Respond** with `{success, file_name, file_hash, chunks_indexed, kb, stats}`.

Any exception in steps 3–7 returns `500` with the exception string — and, importantly, the file has
already been written to disk and may be partially indexed.

<br>

## Persistence per store

| Store | Written where | When |
|---|---|---|
| Chroma | `CHROMA_PATH` (default `./data/databases/vector_db/chroma_db`) | Chroma's `PersistentClient` handles it internally on `add`/`delete` |
| FAISS (opt-in) | `FAISS_PATH` pickle + a sibling `<path>.idx` written by `faiss.write_index` | on every `add_documents`, `delete_by_file`, `clear` |
| BM25 | `BM25_PATH` pickle of `{corpus, metadatas}` | on every mutation; the `BM25Okapi` object itself is *not* pickled, it is rebuilt on load |
| Graph | `GRAPH_PATH` pickle of `{graph, doc_store}` | on every `add_document`, `delete_by_file`, `clear` |
| Registry | `KB_REGISTRY_PATH`, default `<DATABASE_ROOT>/kb_registry.json` | on every mutation, under a `threading.Lock` |

A one-time migration in `registry.py` moves a legacy `./data/kb_registry.json` to the new path on import if
the new one does not exist.

<br>

## Entity extraction (the graph's ingestion step)

`GraphStore._extract_entities(text)` uses three regexes:

| Pattern | Catches | Regex |
|---|---|---|
| Multi-word proper nouns | `Google Cloud`, `New York` | `\b[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})*\b` |
| Acronyms | `LLM`, `RAG`, `API` | `\b[A-Z]{2,6}\b` |
| camelCase terms | `chunkSize`, `fileHash` | `\b[a-z]+(?:[A-Z][a-z]+)+\b` |

Proper-noun matches are filtered against a 24-word `_STOP_WORDS` set (`The`, `This`, `That`, `With`,
`From`, `For`, `And`, `But`, `Are`, `Was`, `Has`, `Have`, `Its`, `Our`, `Their`, `Will`, `Can`, `May`,
`Also`, `Such`, `When`, `Where`, `How`, `What`, `Which`) and must be longer than 2 characters. Acronyms and
camelCase terms are **not** stop-word filtered.

Each chunk becomes a node `{type: "document", content_preview: content[:200], metadata}`; each entity
becomes a node `entity:<lowercased>` with a `count`; the edge between them carries an incrementing
`weight`. Deleting a file removes its document nodes and then any entity node whose degree dropped to 0.

<br>

## Frontend progress model

The upload UI shows two phases because only the first is measurable:

1. **Transfer** — real percentage from axios `onUploadProgress` → `uploadProgress`.
2. **Indexing** — the server gives no progress signal, so `_animateIndexing()` in `stores/rag.js` eases a
   fake bar from 0 toward 95 in steps of 5 every 80 ms, then holds at 95 until the request resolves and
   jumps to 100. `KnowledgeBaseView.vue` labels the phases "Uploading file…", "Processing on server…", and
   "Indexing chunks…", and renders an indeterminate shimmer when the percentage is unknown.

After success the store calls `refreshStats()` then `fetchKnowledgeBases()`.

<br>

## Gotchas

- **Indexing is synchronous and blocks the request.** A large PDF holds the HTTP connection open for the
  entire embed-and-index run.
- **BM25 rebuilds from scratch on every upload.** `_rebuild()` re-tokenises the whole corpus, so ingestion
  cost is O(total corpus), not O(new chunks).
- **The graph pickles once per chunk.** `add_document` calls `_save()` at the end of every chunk, so a
  1000-chunk document writes the entire graph pickle 1000 times. This is the dominant cost of ingesting a
  large file.
- **`edges` in a KB entry is a global count**, so every entry's `edges` reflects the whole graph at the time
  that file was indexed — not that file's own edges.
- **Deleting a KB deletes the uploaded file too**, matched by `kb_entry["name"]` inside `UPLOAD_FOLDER`.
  `/api/clear` does the same for every registered KB, but files left in the folder without a registry entry
  are never cleaned up.
- **No de-duplication across different filenames with identical content** beyond the exact-bytes MD5 — two
  copies of the same document saved under different names index twice, though the aggregator will collapse
  identical chunks at query time.
