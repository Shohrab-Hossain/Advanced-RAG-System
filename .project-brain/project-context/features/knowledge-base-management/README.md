# Feature: Knowledge base management

**Purpose:** let the user add documents to the searchable corpus, see what is indexed and how, and remove
individual documents or wipe everything.

**Entry points:** the `/knowledge-base` route (`KnowledgeBaseView.vue`), the `FileUpload.vue` dropzone, and
the `KnowledgeBases.vue` list. Backend routes `POST /api/upload`, `GET /api/documents`,
`GET /api/knowledge-bases`, `DELETE /api/knowledge-bases/<file_hash>`, `DELETE /api/clear`.

**Implemented in:**

| Concern | File |
|---|---|
| Routes | `Backend/src/app.py` |
| Load + chunk + hash | `Backend/src/rag_pipeline/ingestion/loader.py` |
| Registry persistence | `Backend/src/rag_pipeline/ingestion/registry.py` |
| Store writes/deletes | the three `retrieval/*/*_store.py` modules |
| Upload UI | `Frontend/src/views/KnowledgeBaseView.vue`, `Frontend/src/components/FileUpload.vue` |
| KB list UI | `Frontend/src/components/KnowledgeBases.vue`, `FileTypeIcon.vue`, `StatBadge.vue` |
| Client state | `Frontend/src/stores/rag.js` (`uploadDocument`, `refreshStats`, `fetchKnowledgeBases`, `removeKnowledgeBase`, `clearIndex`) |

**Inputs:** any file whose extension is in `Config.ALLOWED_EXTENSIONS` — **35 of them**
(`config.py:62-65`), spanning documents (`pdf`, `docx`, `txt`, `md`), data (`json`, `csv`), markup
(`html`, `htm`), and source code (`py`, `js`, `ts`, `sh`, `bat`, …) — max 50 MB (`config.py:61`).
**Outputs:** a KB registry entry `{id, name, uploaded_at, chunks, vectors, entities, edges}` plus updated
global index totals.

**Behaviour:**

- A file's **MD5 `file_hash` is its identity**; re-uploading the same bytes replaces the previous index
  entries rather than duplicating them.
- Upload indexes into all three stores in one request; the flow, chunk sizes, and metadata fields are
  specified in [`../../runtime/ingestion-indexing/README.md`](../../runtime/ingestion-indexing/README.md).
- `KnowledgeBaseView.vue` supports **multi-file drag-and-drop** and uploads them sequentially, tracking
  `uploadQueueCurrent` / `uploadQueueTotal`; `FileUpload.vue` handles a single file.
- Deleting a KB removes its chunks from all three stores, drops the registry entry, and deletes the saved
  file from `UPLOAD_FOLDER`. Orphaned entity nodes (degree 0) are pruned from the graph in the same pass.
- `DELETE /api/clear` wipes all three stores, empties the registry, and deletes every registered file.
- Both destructive actions are gated behind `ui.confirm()` in `KnowledgeBases.vue`
  ("Delete this knowledge base?" / "Remove all knowledge bases?").

**Depends on:** the three stores, the shared embedder (upload embeds every chunk), and `ui.js`'s modal for
confirmations. [`hybrid-retrieval`](../hybrid-retrieval/README.md) depends on this feature, not the
reverse.

**Gotchas:**

- **Filename collisions overwrite.** Two different files whose `secure_filename` output matches share one
  path in `UPLOAD_FOLDER`; deleting either deletes the shared file.
- **`edges` in a KB entry is the whole graph's edge count** at index time, not the file's own — only
  `entities` is per-file.
- **The indexing progress bar is synthetic.** The server reports no progress during indexing, so the client
  animates 0→95 and holds; see the ingestion runtime doc.
- **A failed upload can leave partial state** — the file is saved before parsing, and the three store writes
  are not transactional.
- **Deleting from the FAISS backend re-embeds the entire remaining corpus** to rebuild the index; Chroma
  deletes by id.
