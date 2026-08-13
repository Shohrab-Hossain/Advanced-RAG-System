# Feature: Knowledge base management

**Purpose:** let the user add documents to the searchable corpus, see what is indexed and how, and remove
individual documents or wipe everything.

**Entry points:** the `/knowledge-base` route (`KnowledgeBaseView.vue`), the `UploadPanel` dropzone, and
the `KnowledgeBaseList` cards. Backend routes `POST /api/upload`, `GET /api/documents`,
`GET /api/knowledge-bases`, `DELETE /api/knowledge-bases/<file_hash>`, `DELETE /api/clear`.

**Implemented in:**

| Concern | File |
|---|---|
| Routes | `Backend/src/app.py` |
| Load + chunk + hash | `Backend/src/rag_pipeline/ingestion/loader.py` |
| Registry persistence | `Backend/src/rag_pipeline/ingestion/registry.py` |
| Store writes/deletes | the three `retrieval/*/*_store.py` modules |
| Page + confirmations | `Frontend/src/pages/knowledge-base/views/KnowledgeBaseView.vue` (70 lines) |
| Page view-models (pure) | `Frontend/src/pages/knowledge-base/views/knowledgeBaseView.js` — `ACCEPT_ATTR`, `formatDate`, `kbStats`, `buildKbCards`, `buildIndexStats` |
| Upload UI | `Frontend/src/pages/knowledge-base/components/UploadPanel/UploadPanel.vue` |
| Index stat cards | `Frontend/src/pages/knowledge-base/components/IndexStats/IndexStats.vue` |
| KB list UI | `Frontend/src/pages/knowledge-base/components/KnowledgeBaseList/KnowledgeBaseList.vue` + `Frontend/src/shared/components/FileTypeIcon/FileTypeIcon.vue` |
| Client state | `Frontend/src/subsystems/knowledge-base/kbStore.js` — store id **`'knowledgeBase'`** (`uploadDocument`, `refreshStats`, `fetchKnowledgeBases`, `removeKnowledgeBase`, `clearIndex`, `resetUploadResult`, `hasDocuments`) |
| HTTP client | `Frontend/src/subsystems/knowledge-base/kbApi.js` — all five KB routes (`uploadFile`, `getDocuments`, `clearDocuments`, `getKnowledgeBases`, `deleteKnowledgeBase`) |

**Inputs:** any file whose extension is in `Config.ALLOWED_EXTENSIONS` — **35 of them**
(`config.py:62-65`), spanning documents (`pdf`, `docx`, `txt`, `md`), data (`json`, `csv`), markup
(`html`, `htm`), and source code (`py`, `js`, `ts`, `sh`, `bat`, …) — max 50 MB (`config.py:61`). The
browser-side `accept` attribute is the same 35 entries, declared once as `ACCEPT_ATTR`
(`knowledgeBaseView.js:13-20`) and passed down as the `accept` prop; the comment at `:11-12` states the
invariant — *"Mirrors `Config.ALLOWED_EXTENSIONS` … keep the two in step."*
**Outputs:** a KB registry entry `{id, name, uploaded_at, chunks, vectors, entities, edges}` plus updated
global index totals.

**Behaviour:**

- A file's **MD5 `file_hash` is its identity**; re-uploading the same bytes replaces the previous index
  entries rather than duplicating them.
- Upload indexes into all three stores in one request; the flow, chunk sizes, and metadata fields are
  specified in [`../../runtime/ingestion-indexing/README.md`](../../runtime/ingestion-indexing/README.md).
- **The page owns the data; its three components are presentational.** `KnowledgeBaseView.vue:48-49` states
  the contract in the code — *"The children are presentational — the view owns the data and hands each one
  a finished view-model, so no component reaches back up into this folder."* The view builds `indexStats`
  and `kbCards` through the pure `buildIndexStats` / `buildKbCards` (`:50-51`) and passes them as props.
  `IndexStats.vue` imports **nothing** (`:38-41`, props only); `KnowledgeBaseList.vue` emits `remove` /
  `clear` (`:85`) upward instead of calling the store itself.
- **Multi-file upload lives in `UploadPanel.vue`, not in the view.** `handleFiles()`
  (`UploadPanel.vue:125-147`) is reached from both the drop handler (`:155-159`) and the `multiple` file
  input (`:26`, `:149-153`). It uploads sequentially, passing `{queueCurrent, queueTotal}` into
  `store.uploadDocument` (`:143`), which sets `uploadQueueCurrent` / `uploadQueueTotal`
  (`kbStore.js:37-38`) for the `n/total` badge. A per-file failure is swallowed (`catch {}`, `:144`) so the
  batch continues; the message surfaces via `store.uploadResult.error` (`kbStore.js:54`). The status panel
  is cleared **once**, 6 s after the last file (`setTimeout(…, 6000)`, `:146`).
- **Upload progress is two-phase.** Real transfer percentage comes from axios's `onUploadProgress`
  (`kbApi.js:22-26`, wired at `kbStore.js:42`); the server-side indexing phase has no progress signal, so
  `_animateIndexing()` (`kbStore.js:62-76`) eases to 95 in `+5` steps every 80 ms and holds. Between the two
  phases `progressPct` returns `null` (`UploadPanel.vue:117-121`) and the bar renders an indeterminate
  shimmer.
- Deleting a KB removes its chunks from all three stores, drops the registry entry, and deletes the saved
  file from `UPLOAD_FOLDER`. Orphaned entity nodes (degree 0) are pruned from the graph in the same pass.
- `DELETE /api/clear` wipes all three stores, empties the registry, and deletes every registered file.
- **Three confirmations**, all through the `ui` store's promise-based `confirm()` (`store/index.js`):

  | Site | Prompt | Buttons |
  |---|---|---|
  | `KnowledgeBaseView.vue:60` | *"Delete this file from the knowledge base?"* | `danger` · "Yes, delete it" / "No, keep it" |
  | `KnowledgeBaseView.vue:66` | *"Remove all knowledge bases and clear the entire index?"* | `danger` · "Yes, clear all" / "No, keep them" |
  | `UploadPanel.vue:134-137` | *"`<name>` is already in the knowledge base. Re-upload to re-index it?"* | not `danger` · "Yes, re-index it" / "No, keep existing" |

  The third is a **client-side** guard: confirming deletes the existing KB first (`:139`) and then uploads;
  declining skips that file and continues the batch (`:138`).
- **Two components outside this page read `kbStore` — the only cross-subsystem edge in the app.**
  `NavBar.vue:109` calls `kb.refreshStats()` and `kb.fetchKnowledgeBases()` on mount (`:144`) so index
  counts are warm before the page is ever opened, and `ChatView.vue:119` reads `kb.hasDocuments`
  (`kbStore.js:28`) to render the "No documents indexed yet" warning (`ChatView.vue:41`). Everything else
  stays inside one subsystem.

**Depends on:** the three stores, the shared embedder (upload embeds every chunk), and the `ui` store's
modal (`store/index.js`) for confirmations.
[`hybrid-retrieval`](../hybrid-retrieval/README.md) depends on this feature, not the reverse.

**Gotchas:**

- **Filename collisions overwrite.** Two different files whose `secure_filename` output matches share one
  path in `UPLOAD_FOLDER`; deleting either deletes the shared file.
- **The client's duplicate check is by file *name*; the server's identity is the MD5 of the bytes.**
  `UploadPanel.vue:130-132` matches `kb.name.toLowerCase()`, so two genuinely different documents sharing a
  filename raise the re-index prompt, while the same bytes under a different name never do — the backend
  still replaces by hash.
- **`edges` in a KB entry is the whole graph's edge count** at index time, not the file's own — only
  `entities` is per-file.
- **The indexing progress bar is synthetic.** The server reports no progress during indexing, so the client
  animates 0→95 and holds; see the ingestion runtime doc.
- **A failed upload can leave partial state** — the file is saved before parsing, and the three store writes
  are not transactional.
- **Deleting from the FAISS backend re-embeds the entire remaining corpus** to rebuild the index; Chroma
  deletes by id.
