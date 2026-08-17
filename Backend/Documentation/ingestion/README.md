<div align="center">

# 📥 Ingestion

### One uploaded file becomes N chunks that must reach four destinations — three stores and a registry — with no transaction holding them together.

<br>

[![Write targets](https://img.shields.io/badge/write%20targets-4-1c7ed6)](#%EF%B8%8F-3-architecture)
[![Extensions](https://img.shields.io/badge/file%20types-35-7c5cff)](#51-loader-selection)
[![Version](https://img.shields.io/badge/version-0.1.0-3fb950)](../../pyproject.toml)

[![Splitter](https://img.shields.io/badge/splitter-RecursiveCharacter-f59e0b)](https://python.langchain.com/docs/how_to/recursive_text_splitter/)
[![Dedup](https://img.shields.io/badge/dedup-content%20MD5-f59e0b)](#53-dedup-is-delete-then-add-not-upsert)
[![LLM calls](https://img.shields.io/badge/LLM%20calls-0-3fb950)](#56-what-ingestion-costs)

</div>

<br>

---

<br>

## Content Tree

<pre>
Ingestion
│
├── <a href="#-overview">📖 Overview</a>
│
├── <a href="#-1-purpose--user-visible-behavior">🎯 1. Purpose &amp; user-visible behavior</a>
│   ├── <a href="#11-what-the-user-does">1.1 What the user does</a>
│   ├── <a href="#12-what-the-user-sees">1.2 What the user sees</a>
│   └── <a href="#13-what-a-duplicate-upload-does">1.3 What a duplicate upload does</a>
│
├── <a href="#-2-where-it-lives">📍 2. Where it lives</a>
│
├── <a href="#%EF%B8%8F-3-architecture">🏗️ 3. Architecture</a>
│   ├── <a href="#31-four-layers-two-packages">3.1 Four layers, two packages</a>
│   ├── <a href="#32-the-four-write-targets-and-their-asymmetric-call-shapes">3.2 The four write targets, and their asymmetric call shapes</a>
│   └── <a href="#33-the-only-lock-in-the-backend-is-on-the-registry">3.3 The only lock in the backend is on the registry</a>
│
├── <a href="#-4-lifecycle--state-machine">🔄 4. Lifecycle &amp; state machine</a>
│   ├── <a href="#41-the-write-path-end-to-end">4.1 The write path, end to end</a>
│   ├── <a href="#42-the-delete-path">4.2 The delete path</a>
│   └── <a href="#43-the-clear-path">4.3 The clear path</a>
│
├── <a href="#%EF%B8%8F-5-key-algorithms--data-structures">⚙️ 5. Key algorithms &amp; data structures</a>
│   ├── <a href="#51-loader-selection">5.1 Loader selection</a>
│   ├── <a href="#52-chunking-and-why-a-pdf-chunk-never-spans-a-page">5.2 Chunking, and why a PDF chunk never spans a page</a>
│   ├── <a href="#53-dedup-is-delete-then-add-not-upsert">5.3 Dedup is delete-then-add, not upsert</a>
│   ├── <a href="#54-the-chunk-metadata-contract">5.4 The chunk metadata contract</a>
│   ├── <a href="#55-the-registry-entry-shape">5.5 The registry entry shape</a>
│   └── <a href="#56-what-ingestion-costs">5.6 What ingestion costs</a>
│
├── <a href="#-6-wire-shape-cross-boundary-contracts">🔌 6. Wire shape (cross-boundary contracts)</a>
│
├── <a href="#%EF%B8%8F-7-edge-cases--gotchas">⚠️ 7. Edge cases &amp; gotchas</a>
│
├── <a href="#-8-failure-modes">💥 8. Failure modes</a>
│
├── <a href="#-9-extension-points">🧩 9. Extension points</a>
│
└── <a href="#-10-related-decisions--deeper-reading">🔗 10. Related decisions &amp; deeper reading</a>
</pre>

<br>

---

<br>

## 📖 Overview

Ingestion is the **write half** of the RAG system: the path a file takes from a multipart upload to
being searchable by all three retrieval stores. It loads the file with one of six LangChain loaders,
splits it into overlapping character chunks, hashes its **content** to an MD5 that becomes the knowledge
base's id, then writes the chunks into the dense vector index, the BM25 keyword index and the NetworkX
entity graph — and records the file in a JSON registry so the UI can list and delete it.

There is no background job, no queue, and no LLM. `POST /api/upload` runs the whole thing synchronously
on the request thread and returns the resulting statistics in its response body.

> [!IMPORTANT]
> **Four destinations, no transaction.** Every ingest and every delete must touch **all three stores and
> the registry**, and nothing enforces that. The module docstring of `services.py:6-9` states it
> outright: *"There are no transactions and no cross-store lock, so a partial write leaves the corpus
> inconsistent with nothing surfaced — which is why the ordering here is fixed and why the routes call
> these functions rather than reaching into a store."* The fixed ordering inside
> `index_document` (`services.py:44`) **is** the consistency mechanism. There is no other one.

**Where this fits:** the stores it writes into are documented in
[`../hybrid-retrieval/stores.md`](../hybrid-retrieval/stores.md); the read path that consumes what
ingestion produces is [`../hybrid-retrieval/README.md`](../hybrid-retrieval/README.md); the settings that
tune it are in [`../configuration.md`](../configuration.md).

---

## 🎯 1. PURPOSE & USER-VISIBLE BEHAVIOR

### 1.1 What the user does

The user drops a file on the knowledge-base page, which issues one `POST /api/upload` with a multipart
`file` field. **35 extensions are accepted** — `pdf`, `txt`, `md`, `docx`, `json`, `csv`, `html`, `htm`
and 27 code/markup extensions (`config.py:70-73`). Anything else is rejected with a `400` whose message
lists the full sorted set.

The request body is capped at **50 MB** by `Config.MAX_CONTENT_LENGTH` (`config.py:69`), which Flask
enforces through `app.config.from_object(Config)` (`app.py:35`).

There is no progress stream for ingestion. Unlike a query — which streams
[Server-Sent Events](../sse-event-bus/README.md) as it runs — an upload is a plain request/response that
blocks until every store has been written.

### 1.2 What the user sees

The response carries the per-file result and the new corpus-wide totals:

```json
{
  "success": true,
  "file_name": "quarterly-report.pdf",
  "file_hash": "9d5f0c2e1b7a44c8bb1f6e2a03d9c471",
  "chunks_indexed": 84,
  "kb": {
    "id": "9d5f0c2e1b7a44c8bb1f6e2a03d9c471",
    "name": "quarterly-report.pdf",
    "uploaded_at": "2026-08-16T09:41:02.884213+00:00",
    "chunks": 84, "vectors": 84, "entities": 37, "edges": 512
  },
  "stats": {
    "vector_total": 84,
    "bm25_total": 84,
    "graph": { "documents": 84, "entities": 37, "edges": 512 }
  }
}
```

`kb` is the registry entry (`registry.py:45-53`) and drives the knowledge-base list; `stats` is
`totals()` (`services.py:33-39`) and drives the index-statistics panel.

### 1.3 What a duplicate upload does

**Nothing rejects it, and nothing warns about it.** No route compares the incoming file against the
registry. Re-uploading the same bytes is an **idempotent re-index**: the same content hash produces the
same knowledge-base id and the same deterministic chunk ids, and `index_document` deletes the previous
copy before writing the new one. The visible result is one registry entry with a refreshed
`uploaded_at`, an unchanged chunk count, and unchanged totals.

The interesting cases are the *near*-duplicates — same bytes under a different name, and different bytes
under the same name. Both have surprising outcomes; see [§7](#%EF%B8%8F-7-edge-cases--gotchas).

---

## 📍 2. WHERE IT LIVES

Paths are relative to the package root, `Backend/src/adrag/`.

| Concern | Path | Anchor |
|---|---|---|
| HTTP framing | `routes/knowledge_base/knowledge_base_routes.py:42` | `upload` |
| Extension gate | `routes/knowledge_base/knowledge_base_routes.py:28` | `_allowed` |
| Orchestration | `routes/knowledge_base/services.py:44` | `index_document` |
| Delete orchestration | `routes/knowledge_base/services.py:86` | `remove_document` |
| Wipe orchestration | `routes/knowledge_base/services.py:94` | `clear_everything` |
| Load + chunk | `custom_packages/rag_pipeline/ingestion/loader.py:74` | `load_file` |
| Loader selection | `custom_packages/rag_pipeline/ingestion/loader.py:57` | `_get_loader` |
| Content hash | `custom_packages/rag_pipeline/ingestion/loader.py:48` | `_hash_file` |
| Chunk ids | `custom_packages/rag_pipeline/ingestion/loader.py:114` | `generate_chunk_ids` |
| KB registry | `custom_packages/rag_pipeline/ingestion/registry.py:41` | `register`, `remove`, `list_all`, `clear_all` |

```text
custom_packages/rag_pipeline/ingestion/
│
├── 📄 __init__.py             A one-line docstring — exports nothing
├── 📄 loader.py               Bytes → (texts, metadatas); the splitter, the hash, the chunk ids
└── 📄 registry.py             The JSON manifest of which files are indexed, and their stats

routes/knowledge_base/
│
├── 📄 knowledge_base_routes.py   5 routes — validation, secure_filename, status codes. No store access
└── 📄 services.py                The fixed order in which the 3 stores and the registry are written
```

> [!NOTE]
> **The subsystem is deliberately split across two packages.** `loader.py` and `registry.py` live inside
> the pipeline package and never import Flask; `services.py` lives behind the route and is the only file
> in the backend that knows all four write targets exist. That split is what lets the pipeline be
> imported and driven headlessly, and it is the same layering rule the nodes follow.

---

## 🏗️ 3. ARCHITECTURE

### 3.1 Four layers, two packages

| Layer | File | Lines | Responsibility |
|---|---|---|---|
| HTTP framing | `routes/knowledge_base/knowledge_base_routes.py` | 97 | validation, `secure_filename`, status codes — **no store access** |
| Orchestration | `routes/knowledge_base/services.py` | 115 | the fixed order in which the three stores and the registry are written |
| Load + chunk | `…/ingestion/loader.py` | 117 | bytes → `(texts, metadatas)`; owns the splitter, the hash, the chunk ids |
| Registry | `…/ingestion/registry.py` | 88 | the JSON manifest of *which files are indexed* + their per-file stats |

`ingestion/__init__.py` is a single docstring line and exports nothing, so every consumer imports the
module directly — `from …ingestion.loader import load_file, generate_chunk_ids` and
`from …ingestion import registry as kb_registry` (`services.py:18-19`).

### 3.2 The four write targets, and their asymmetric call shapes

The three stores do **not** share one call signature, and the difference is structural rather than
cosmetic:

| Target | Call | Identity | Batching |
|---|---|---|---|
| Vector store | `add_documents(texts, metadatas, chunk_ids)` | ids passed explicitly | one batch call |
| BM25 store | `add_documents(texts, metadatas)` | **no `ids` parameter exists** (`bm25_store.py:67`) — identity is list position | one batch call |
| Graph store | `add_document(chunk_ids[i], text, meta)` | id passed per chunk | **once per chunk** (`graph_store.py:65`) |
| KB registry | `register(file_hash, filename, stats)` | keyed by content hash | once per file |

A new retriever that copies the BM25 shape drops straight into the existing loop; one that copies the
graph shape does not. The per-method surface of each store is tabulated in
[`../hybrid-retrieval/stores.md`](../hybrid-retrieval/stores.md).

### 3.3 The only lock in the backend is on the registry

`registry.py:22` declares `_lock = threading.Lock()`, and every public function holds it —
`register` (`:43`), `get` (`:61`), `list_all` (`:67`), `remove` (`:76`), `clear_all` (`:86`). Grep the
three store modules and `services.py` for `threading.Lock` and you find **nothing**.

So the one component in the backend with explicit thread synchronisation is the **metadata manifest**,
not the data it describes. Two simultaneous uploads cannot corrupt `kb_registry.json` mid-write, but they
can absolutely interleave their writes into the BM25 corpus, the graph pickle and the Chroma collection.
**Concurrent ingest is the unsafe operation in this system**; concurrent query is read-only against the
same structures and is fine.

---

## 🔄 4. LIFECYCLE & STATE MACHINE

### 4.1 The write path, end to end

<p align="center">
  <img src="../../../.readme-lib/documentation/ingestion/diagrams/svg/ingestion-flow.svg" alt="The ingestion write path: a multipart POST /api/upload meets _allowed(), the first of two extension checks — a rejected suffix exits as 400 unsupported file type. An allowed file is written to disk with secure_filename before os.path.join, the sole path-traversal defence. load_file() then picks 1 of 6 LangChain loaders by suffix, splits with RecursiveCharacterTextSplitter at 500 characters and 50 overlap into N chunks, and takes an MD5 of the file content as file_hash. If no text was extracted the run exits as 422. Otherwise generate_chunk_ids produces deterministic file_hash underscore index ids, remove_document(file_hash) runs first — delete before write, which is the whole dedup mechanism — and the run fans out to FOUR write targets with no transaction and no cross-store lock: vector_store.add_documents in one batch call with ids, bm25_store.add_documents in one batch call with no ids, graph_store.add_document once per chunk which re-pickles the whole graph each time, and kb_registry.register recording chunks, vectors, entities and edges. The response is 200 carrying chunks_indexed, kb and stats." width="700">
</p>

<sub>Diagram source: <a href="../../../.readme-lib/documentation/ingestion/diagrams/mermaid-source/ingestion-flow.mmd"><code>ingestion-flow.mmd</code></a> — edit it, then regenerate the SVG (don't hand-edit the SVG).</sub>

**Steps 1–3 — the route's three gates** (`knowledge_base_routes.py:42-59`). A missing `file` field, an
empty filename, or a disallowed extension each return `400` before anything touches disk. `_allowed`
(`:28-37`) is a pure suffix test against `Config.ALLOWED_EXTENSIONS`, and its docstring names itself the
**first of two extension checks** — the second is `_get_loader`'s `ValueError` (`loader.py:71`), which
decides which loader actually runs. **Content is never sniffed**; the extension is trusted to describe
the bytes.

**Step 4 — save, in this exact order:**

```python
# routes/knowledge_base/knowledge_base_routes.py:56
# secure_filename runs BEFORE the join — it is the sole path-traversal defence here.
filename = secure_filename(f.filename)
file_path = os.path.join(Config.UPLOAD_FOLDER, filename)
f.save(file_path)
```

`Config.UPLOAD_FOLDER` is created at factory time (`os.makedirs(..., exist_ok=True)`, `app.py:49`), so
the save never fails for a missing directory.

**Step 5 — load and chunk**, then the empty-extraction gate:

```python
# routes/knowledge_base/services.py:52
texts, metadatas = load_file(file_path)
if not texts:
    raise ValueError("No text could be extracted from this file")
```

The route turns that `ValueError` into a **`422`** (`knowledge_base_routes.py:64-65`). The docstring at
`services.py:49-50` gives the reason: *"an empty index write would otherwise register a knowledge base
nothing can retrieve."* The realistic triggers are a scanned PDF with no text layer, a zero-byte file, or
an HTML page that is entirely markup.

**Steps 6–9 — ids, delete-then-write, register.** The order below is verbatim and load-bearing:

```python
# routes/knowledge_base/services.py:56
file_hash = metadatas[0].get("file_hash", fallback_hash)
chunk_ids = generate_chunk_ids(file_hash, len(texts))

# Remove any existing data for this file before re-indexing
remove_document(file_hash)

# Index into all three stores
vector_store.add_documents(texts, metadatas, chunk_ids)
bm25_store.add_documents(texts, metadatas)
for i, (text, meta) in enumerate(zip(texts, metadatas)):
    graph_store.add_document(chunk_ids[i], text, meta)

graph_stats = graph_store.get_stats()
kb_entry = kb_registry.register(file_hash, filename, {
    "chunks": len(texts),
    "vectors": len(texts),   # 1 chunk → 1 embedding
    "entities": graph_store.count_entities_by_file(file_hash),
    "edges": graph_stats.get("edges", 0),
})
```

**Step 10 — respond.** `index_document` returns `(payload, chunk_count)`; the route serialises the
payload as-is (`services.py:76-83`).

### 4.2 The delete path

`remove_document(file_hash)` (`services.py:86-91`) mirrors the write order exactly — vector, BM25,
graph, registry — and **returns nothing**:

```python
# routes/knowledge_base/services.py:86
def remove_document(file_hash: str) -> None:
    """Drop one file from all three stores and the registry. Order is deliberate."""
    vector_store.delete_by_file(file_hash)
    bm25_store.delete_by_file(file_hash)
    graph_store.delete_by_file(file_hash)
    kb_registry.remove(file_hash)
```

The first two store deletes return removal counts and the third returns `None`; **every return value is
discarded**. A delete that removed zero vectors and forty BM25 rows reports exactly the same thing as a
clean one: nothing.

`remove_document` also does **not** delete the uploaded file. That is the route's job, and only the
per-KB delete route does it — `services.delete_upload(kb_entry["name"])` (`knowledge_base_routes.py:95`),
guarded by the registry lookup that precedes it.

### 4.3 The clear path

`clear_everything()` (`services.py:94-104`) snapshots the registry **first**, then wipes:

```python
# routes/knowledge_base/services.py:94
all_kbs = kb_registry.list_all()

vector_store.clear()
bm25_store.clear()
graph_store.clear()
kb_registry.clear_all()

for kb in all_kbs:
    delete_upload(kb["name"])
```

The snapshot is what makes the file cleanup possible at all — once `clear_all()` has run there is no
record of which names were uploaded. The direct consequence is that **only files named in the registry
are removed from disk**: an orphan left behind by a failed ingest (§7) is never reached by
`DELETE /api/clear`, permanently. `delete_upload` (`:107-114`) swallows `OSError` and treats a missing
file as success.

---

## ⚙️ 5. KEY ALGORITHMS & DATA STRUCTURES

### 5.1 Loader selection

**The problem:** eight document formats and 27 code extensions must all become plain text, and the
choice has to be made from the filename alone because content is never sniffed.

`_get_loader` (`loader.py:57-71`) is a suffix `if`-chain over six LangChain loaders:

| Extension | Loader | Line |
|---|---|---|
| `.pdf` | `PyPDFLoader(file_path)` | `:59-60` |
| `.docx` | `Docx2txtLoader(file_path)` | `:61-62` |
| `.md` | `UnstructuredMarkdownLoader(file_path)` | `:63-64` |
| `.html` · `.htm` | `BSHTMLLoader(file_path, open_encoding="utf-8")` | `:65-66` |
| `.csv` | `CSVLoader(file_path, encoding="utf-8")` | `:67-68` |
| any of the 29 in `_TEXT_EXTENSIONS` | `TextLoader(file_path, encoding="utf-8")` | `:69-70` |
| anything else | `raise ValueError(f"Unsupported file type: {ext}")` | `:71` |

`_TEXT_EXTENSIONS` (`loader.py:28-33`) holds 29 entries — `.txt`, `.json`, and 27 code/markup
extensions. **Every one of them is read as plain UTF-8 text.** There is no language-aware splitter, so a
`.py` file is chunked by exactly the same character rules as a novel.

`SUPPORTED_EXTENSIONS` (`loader.py:35-45`) maps extension → the `source_type` string stamped on every
chunk. It is eight named entries plus a comprehension over `_TEXT_EXTENSIONS - {".txt", ".json"}` mapped
to `"code"` — so `.txt` is `"text"`, `.json` is `"json"`, and the other 27 all collapse to `"code"`.
**35 extensions total, exactly equal to `Config.ALLOWED_EXTENSIONS`.** The double check is redundant
today; it exists to catch drift between the two files, which live in different packages.

### 5.2 Chunking, and why a PDF chunk never spans a page

**The problem:** an embedding model and a BM25 index both want passages of a few hundred characters,
while a source document is thousands. Splitting has to respect natural boundaries where they exist and
still guarantee termination where they do not.

```python
# custom_packages/rag_pipeline/ingestion/loader.py:84
splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    separators=["\n\n", "\n", ".", " ", ""],
)
split_docs = splitter.split_documents(raw_docs)
```

- **Defaults are 500 characters with 50 of overlap** — `CHUNK_SIZE` and `CHUNK_OVERLAP`
  (`loader.py:24-25`), both read with `os.getenv` at **module scope** and therefore frozen at import.
- **The separator ladder is paragraph → line → sentence → word → character.** The empty-string fallback
  guarantees a split always succeeds, so a 4 000-character run with no whitespace is cut mid-word rather
  than left oversized.
- **`split_documents`, not `split_text`.** The loader's per-document metadata — notably a PDF's `page` —
  survives into every chunk. This is the only reason source cards can show a page number.
- **Chunking is per-document, not per-file.** `PyPDFLoader` yields one LangChain `Document` per page, so
  a PDF is split page by page and **a chunk never spans a page boundary**: a 40-character trailing
  paragraph on page 3 becomes its own 40-character chunk. `TextLoader` yields exactly one document, so a
  `.txt` or code file is split as one continuous run.

### 5.3 Dedup is delete-then-add, not upsert

**The problem:** users re-upload. Without something, the second upload doubles every chunk and the
retriever returns the same passage twice.

There is **no duplicate-detection branch anywhere in the backend**. Dedup emerges from three facts
composing:

1. **The knowledge-base id is the content MD5.** `_hash_file` (`loader.py:48-54`) streams the file in
   4 096-byte blocks through `hashlib.md5` — so the hash is cheap on a 50 MB file, and it is a hash of
   the **content, not the filename**.

   ```python
   # custom_packages/rag_pipeline/ingestion/loader.py:48
   def _hash_file(file_path: str) -> str:
       """MD5 hash of file content — used for stable chunk IDs and dedup."""
       h = hashlib.md5()
       with open(file_path, "rb") as f:
           for block in iter(lambda: f.read(4096), b""):
               h.update(block)
       return h.hexdigest()
   ```

2. **Chunk ids are deterministic.** `generate_chunk_ids` (`loader.py:114-116`) returns
   `[f"{file_hash}_{i}" for i in range(count)]`, so identical bytes always produce an identical id set.

3. **`index_document` calls `remove_document(file_hash)` before writing anything** (`services.py:60`).
   All three stores and the registry entry are dropped first.

> [!WARNING]
> **"Upsert" is the wrong word, and the distinction is load-bearing.** `generate_chunk_ids`' docstring
> says the ids exist *"for Chroma upsert dedup"* (`loader.py:115`) — but `ChromaVectorStore.add_documents`
> calls `self.collection.add(...)` (`vector_store.py:69`), never `upsert`. Deterministic ids alone would
> **not** deduplicate; adding the same id twice to a Chroma collection is not a silent replace. **The
> delete-before-write at `services.py:60` is the entire mechanism.** Remove that one line believing the
> ids cover you and re-uploads start corrupting the corpus.

### 5.4 The chunk metadata contract

One dict per chunk, built at `loader.py:99-109` and passed **verbatim** to all three stores:

| Key | Value | Note |
|---|---|---|
| `file_name` | `Path(file_path).name` | the **sanitised** name, post-`secure_filename` |
| `file_path` | the full server-side path | absolute; leaks the server layout into every retrieved document |
| `file_hash` | the content MD5 | the KB id, and the delete key for all three stores |
| `chunk_index` | `i`, 0-based | |
| `total_chunks` | `len(split_docs)` | |
| `source_type` | `SUPPORTED_EXTENSIONS.get(ext, "unknown")` | one of `pdf` · `text` · `markdown` · `docx` · `json` · `csv` · `html` · `code` |
| `page` | `int(doc.metadata["page"])` — **only when the loader supplied one** | `:107-108`; in practice PDFs only |

Because `page` is conditional and web-search results carry a **disjoint** key set entirely, every
downstream consumer reads this dict defensively (`meta.get("file_name") or meta.get("title") or …`).
The per-source metadata matrix is in [`../hybrid-retrieval/stores.md`](../hybrid-retrieval/stores.md).

### 5.5 The registry entry shape

`register` (`registry.py:41-56`) writes exactly seven keys under the file hash:

```python
# custom_packages/rag_pipeline/ingestion/registry.py:45
entry = {
    "id": file_hash,
    "name": file_name,
    "uploaded_at": datetime.now(timezone.utc).isoformat(),
    "chunks": stats.get("chunks", 0),
    "vectors": stats.get("vectors", 0),
    "entities": stats.get("entities", 0),
    "edges": stats.get("edges", 0),
}
```

`chunks` and `vectors` are both `len(texts)` — one chunk yields one embedding, as the in-code comment at
`services.py:71` says. `entities` is genuinely per-file: `count_entities_by_file`
(`graph_store.py:140-151`) walks this file's chunk nodes and counts the distinct entity nodes adjacent
to them.

> [!CAUTION]
> **`edges` is the whole graph's edge count, not this knowledge base's — so every row reports the same
> number.** `services.py:73` reads `graph_stats.get("edges", 0)` from `graph_store.get_stats()`, whose
> `edges` field is `self.graph.number_of_edges()` (`graph_store.py:159`) — a corpus-wide total.
> `entities` is per-file; `edges` is not. The consequence compounds: each new upload raises the true
> total, but older registry rows keep whatever the total happened to be when *they* were indexed. A list
> of five knowledge bases therefore shows five different frozen snapshots of one global number, none of
> which describes the row it sits on. Read `edges` as corpus-wide-at-index-time, or ignore it.

### 5.6 What ingestion costs

For one file producing `N` chunks, at the defaults:

| Work | Count | Evidence |
|---|---|---|
| MD5 passes over the file | 1, streamed in 4 KB blocks | `loader.py:50-53` |
| Embedding forward passes | `N` (one batch call) | `vector_store.py:66` |
| Entity-regex passes | `N` (three regexes each) | `graph_store.py:49-61`, called from `:67` |
| **Graph pickle writes** | **`N`** | `graph_store.py:85`, inside the `services.py:65-66` loop |
| BM25 re-tokenise + index rebuild | 1, over the **whole corpus** | `bm25_store.py:44-47` |
| BM25 pickle writes | 1 | `bm25_store.py:49-51` |
| Registry JSON read + write | 1 each | `registry.py:44`, `:55` |
| **LLM calls** | **0** | no `get_llm` import in `loader.py`, `registry.py` or `services.py` |

> [!WARNING]
> **`graph_store.add_document` ends with `self._save()`, and `services.py` calls it once per chunk.** A
> 200-chunk PDF therefore performs **200 full pickle dumps of the entire graph** — each one larger than
> the last, because it serialises the whole corpus-wide `nx.Graph` plus `doc_store`, not this file's
> slice. That is quadratic write amplification and it is the dominant disk cost of ingestion. BM25 is
> gentler but not free: one pickle write per file, though it re-tokenises and rebuilds `BM25Okapi` over
> the **whole corpus** on every write. Only Chroma writes incrementally.

**Ingestion never calls an LLM.** Entity extraction for the graph is three regexes over the chunk text,
not a named-entity-recognition model; the only model that runs during an upload is the
SentenceTransformer embedder.

---

## 🔌 6. WIRE SHAPE (CROSS-BOUNDARY CONTRACTS)

**HTTP in.** Five routes touch this subsystem, all in `knowledge_base_routes.py`. Full request/response
detail lives in [`../api/knowledge-base.md`](../api/knowledge-base.md); the ingestion-relevant contract
is:

| Direction | Endpoint | Payload | Statuses |
|---|---|---|---|
| Client → server | `POST /api/upload` | multipart, field `file` | `200` · `400` (no field / empty name / bad extension) · `422` (no text extracted) · `500` (anything else) · `413` (over 50 MB) |
| Client → server | `DELETE /api/knowledge-bases/<file_hash>` | path param | `200` always |
| Client → server | `DELETE /api/clear` | none | `200` always |
| Client → server | `GET /api/knowledge-bases` | none | `200` — `{"knowledge_bases": [...]}` |
| Client → server | `GET /api/documents` | none | `200` — `index_stats()` |

> [!NOTE]
> **The 413 breaks the JSON error contract.** Every handwritten failure returns `{"error": "..."}`, but
> **no `errorhandler` is registered anywhere in the backend**, so a request body over
> `MAX_CONTENT_LENGTH` is rejected by Werkzeug before any route runs and the client receives Werkzeug's
> default **HTML** 413 page. A frontend that assumes JSON on every non-2xx will fail to parse it.

**Process → disk.** Four independent writes with no shared transaction:

| Target | Path | Format | Write granularity |
|---|---|---|---|
| Uploaded file | `${UPLOAD_FOLDER}/<secure_filename>` | verbatim bytes | once per upload |
| Vector index | `${CHROMA_PATH}` (default) | Chroma SQLite + binary segments | incremental |
| Keyword index | `${BM25_PATH}` | pickle of `{corpus, metadatas}` | whole file, once per upload |
| Entity graph | `${GRAPH_PATH}` | pickle of `{graph, doc_store}` | whole file, **once per chunk** |
| Registry | `${KB_REGISTRY_PATH}` | JSON object keyed by file hash | whole file, under a lock |

Every one of those paths is resolved in [`../configuration.md`](../configuration.md).

---

## ⚠️ 7. EDGE CASES & GOTCHAS

- **Same bytes, different filename → the entry silently renames and the old file is orphaned.** The
  content hash is identical, so `register(file_hash, filename, …)` (`registry.py:41`) overwrites the
  entry with the **new** name. The first upload's file is still sitting in `data/uploads/` under the old
  name, and nothing references it any more — `remove_document` never calls `delete_upload`, and
  `clear_everything` only deletes names it finds in the registry.

- **Different bytes, same filename → two registry entries share one file on disk, and deleting either
  breaks the other.** Different hashes mean two knowledge bases, both indexed. But `f.save()` already
  overwrote the file, so one entry's `name` now points at bytes that are gone; and because the per-KB
  delete route removes `kb_entry["name"]` from disk (`knowledge_base_routes.py:95`), deleting **either**
  KB removes the shared file. **`secure_filename` collisions are unhandled** — there is no uniquifying
  suffix anywhere in the upload path.

- **A failed ingest orphans the uploaded file, permanently.** `f.save()` runs at
  `knowledge_base_routes.py:59`, before `index_document`; no `except` branch removes it. A `422` (no
  extractable text) or a `500` (anything else) therefore leaves a file in `data/uploads/` that nothing
  references — and `DELETE /api/clear` will **not** remove it either, because `clear_everything` only
  deletes files named in the registry (§4.3). The only cleanup is manual.

- **`secure_filename` is the sole path-traversal defence, and its position matters.** It runs *before*
  the `os.path.join` (`knowledge_base_routes.py:56-58`). Reorder those two lines and the route accepts
  `../../etc/whatever`. There is no second check downstream.

- **Both extension checks are load-bearing even though they currently agree.**
  `Config.ALLOWED_EXTENSIONS` and `loader.SUPPORTED_EXTENSIONS` are exactly equal today, so the
  `_get_loader` `ValueError` is unreachable through the HTTP route. It is the backstop for the drift
  between two files in two packages, and for any caller that reaches `load_file` without going through
  the route.

- **All 27 code extensions are one `source_type`.** A `.py`, a `.sql` and a `.dart` chunk are all stamped
  `"code"`, and none of them is split on language boundaries. Filtering retrieved chunks by language is
  not possible from the metadata as stored.

- **`file_path` metadata leaks the server layout.** Every chunk carries the absolute server-side path of
  its source file (`loader.py:101`), and that metadata travels into the vector store, the BM25 store, the
  graph store, the retrieval results, and — for cited sources — the query response the browser receives.

- **`fallback_hash` is effectively dead code.** The route mints `str(uuid.uuid4())` and passes it
  (`knowledge_base_routes.py:62`), but it is only used if the first chunk's metadata lacks `file_hash`,
  which `load_file` always sets (`loader.py:102`). It is defensive, not reachable.

- **`CHUNK_SIZE` and `CHUNK_OVERLAP` work but are undiscoverable.** `loader.py:24-25` reads them
  directly from the environment, so setting them in `.env` genuinely changes chunking — yet **there is no
  chunking section in `.env.example` at all**. Both are also frozen at import; changing them requires a
  restart *and* a re-index, since existing chunks keep the size they were split at. See
  [`../configuration.md`](../configuration.md).

- **The registry migrates a legacy path at import time.** `registry.py:18-21` checks for
  `./data/kb_registry.json` — relative to the process working directory — and `shutil.move`s it to the
  configured path if the configured one does not exist. It is a one-shot migration from the era when
  `DATA_ROOT` resolved against the cwd, and it runs on **every** import of the module.

- **Delete counts are computed and thrown away.** `BM25Store.delete_by_file` and the vector stores both
  return the number of rows removed; `remove_document` (`services.py:88-91`) discards all of them. There
  is no way, from the API, to tell a delete that removed 84 chunks from one that removed none.

---

## 💥 8. FAILURE MODES

| Failure | Symptom | Behaviour |
|---|---|---|
| No `file` field / empty filename / bad extension | `400` with a JSON `error` | Nothing written; no file saved |
| Request body over 50 MB | Werkzeug's **HTML** `413` | Rejected before the route runs |
| Loader raises (corrupt PDF, bad encoding) | `500` with `str(exc)` | **The saved file stays on disk** as an orphan |
| No text extracted | `422` *"No text could be extracted from this file"* | Same — the file is saved and orphaned |
| Crash between two store writes | `500` | **The stores already written stay written**; the registry entry is never created, so the UI cannot see or delete the partial document |
| Corrupt `bm25_store.pkl` / `graph_store.pkl` | **None** — no log line, no exception | The store silently resets to empty and the next write persists that emptiness |
| Corrupt `kb_registry.json` | **None** | Reads as `{}`; see the caution below |
| FAISS delete of the last indexed file | `ValueError: not enough values to unpack` → `500` | Opt-in backend only; see the caution below |

**Concretely, what a partial write looks like.** A crash between `bm25_store.add_documents`
(`services.py:64`) and the graph loop (`:65-66`) leaves the document searchable by keyword **and** by
vector, invisible to the graph, and absent from the registry. `GET /api/knowledge-bases` will not list
it, so there is no UI path to delete it. The only recovery is `DELETE /api/clear`.

> [!CAUTION]
> **A corrupt registry plus one upload silently destroys every other knowledge-base record.**
> `_load()` (`registry.py:25-32`) catches **every** exception and returns `{}`:
>
> ```python
> # custom_packages/rag_pipeline/ingestion/registry.py:25
> def _load() -> dict:
>     if os.path.exists(_REGISTRY_PATH):
>         try:
>             with open(_REGISTRY_PATH) as f:
>                 return json.load(f)
>         except Exception:
>             pass
>     return {}
> ```
>
> `register()` then does `data = _load()` → `data[file_hash] = entry` → `_save(data)` (`:44-55`). So one
> unreadable or truncated `kb_registry.json`, followed by a single upload, **overwrites the file with
> exactly one entry and permanently discards every other record** — while all three stores still hold
> those documents' chunks. The corpus becomes searchable-but-unlistable and undeletable through the UI,
> which is precisely the inconsistency the fixed write ordering exists to prevent, arriving through the
> back door. There is no backup, no `.bak`, and no warning on any of it.

> [!WARNING]
> **The pickle-backed stores load under a bare `except` and silently reset to empty.**
> `bm25_store.py:53-63` sets `self.corpus = []; self.metadatas = []` on any exception;
> `graph_store.py:173-182` sets `self.graph = nx.Graph(); self.doc_store = {}`; the FAISS store
> (`vector_store.py:138-154`) does the same across five attributes. A version-incompatible or truncated
> pickle is therefore discarded with **no log line, no exception and no warning** — the store starts
> empty and the next write persists that emptiness. The failure is asymmetric: Chroma is the default
> vector backend and persists through its own SQLite with no such handler, so a corrupt BM25 pickle
> silently empties keyword search while vector search keeps working and the totals panel keeps showing a
> healthy vector count.

> [!WARNING]
> **`FaissVectorStore.delete_by_file` raises when it removes the *last* indexed file.** After the filter
> loop, `vector_store.py:227` runs `self.ids, self.documents, self.metadatas = map(list, zip(*kept))`
> unguarded. When `kept` is empty — the deleted file was the only one indexed — `zip(*[])` yields nothing
> and the three-way unpack raises `ValueError: not enough values to unpack`. `BM25Store.delete_by_file`
> guards the identical case (`bm25_store.py:95-98`: `if kept: … else: self.corpus, self.metadatas = [], []`);
> the FAISS path does not. It is reachable through `DELETE /api/knowledge-bases/<hash>` **and** through a
> plain re-upload, because that calls `remove_document` first. **Opt-in path only — this cannot happen on
> the default Chroma backend.**

---

## 🧩 9. EXTENSION POINTS

**Add a file type.** Two files, and missing either one breaks it differently. Add the extension to
`Config.ALLOWED_EXTENSIONS` (`config.py:70-73`) or the route rejects it with a `400`; add it to
`loader.SUPPORTED_EXTENSIONS` and `_get_loader` (`loader.py:35-71`) or `load_file` raises
`ValueError: Unsupported file type` and the route turns that into a `422`. If the new type needs its own
loader, add a branch to `_get_loader`; if plain UTF-8 text will do, adding it to `_TEXT_EXTENSIONS`
(`loader.py:28-33`) is enough — but note it will then be typed `"code"` by the comprehension at `:44`
unless you give it a named entry.

**Add a fourth write target.** Add the call to `index_document` (`services.py:63-66`) **after** the
`remove_document` line, add the matching delete to `remove_document` (`:88-91`), and add the wipe to
`clear_everything` (`:98-101`). All three, or the delete-then-write dedup stops covering your store. The
store surface to implement is in [`../hybrid-retrieval/README.md`](../hybrid-retrieval/README.md) §9.

**Change chunking.** `CHUNK_SIZE` / `CHUNK_OVERLAP` in the environment, or the `separators` ladder at
`loader.py:87` for a genuinely different splitting strategy. Either change requires re-indexing every
document — existing chunks keep the shape they were written with, and the stores have no migration path.

**Promote `KB_REGISTRY_PATH` to `Config`.** It is read directly at `registry.py:15`, the one setting in
the backend that is not a `Config` attribute. If you touch that file, move it — the convention it breaks
is documented in [`../configuration.md`](../configuration.md).

**What not to touch.** Do not remove the `remove_document(file_hash)` call at `services.py:60` on the
theory that deterministic ids handle dedup — they do not (§5.3). Do not reorder `secure_filename` and
`os.path.join` (§7). Do not make the three store writes concurrent: they share no lock, and the two
pickle stores rewrite their whole file on every save.

---

## 🔗 10. RELATED DECISIONS & DEEPER READING

- **Content-addressed knowledge bases.** Identifying a knowledge base by the MD5 of its bytes rather
  than by filename or a generated id buys idempotent re-indexing for free: the same document uploaded
  twice, under any name, converges on one entry. The cost is that identity is invisible to the user —
  they think in filenames, the system thinks in hashes — which is the direct cause of both surprising
  duplicate cases in §7. A filename-keyed design would trade those for the opposite pathology.

- **Delete-then-write instead of a real upsert.** None of the three stores exposes a uniform upsert, and
  two of them (BM25, graph) have no id-addressable update at all. Deleting the whole file's footprint
  and rewriting it is the only operation all three support identically, which is why it is the mechanism
  rather than a per-store optimisation. It is also why a re-index is O(whole file) even for a one-word
  edit.

- **Synchronous ingestion on the request thread.** There is no queue and no worker. A large PDF holds
  the HTTP connection for the duration of embedding, entity extraction and N pickle dumps. For a
  single-user localhost tool that is a feature — the response genuinely means *indexed* — but it is the
  first thing that breaks under real concurrency, and it composes badly with the total absence of
  cross-store locking (§3.3).

- **Statistics recorded at index time, never recomputed.** The registry stores counts rather than
  deriving them, so listing knowledge bases is one JSON read instead of three store scans. The trade is
  that the numbers are snapshots, and one of them (`edges`) was never per-file to begin with (§5.5).

**Continue reading:**

- [`../hybrid-retrieval/README.md`](../hybrid-retrieval/README.md) — the read path over what ingestion writes
- [`../hybrid-retrieval/stores.md`](../hybrid-retrieval/stores.md) — the three stores, method by method
- [`../configuration.md`](../configuration.md) — every path, chunk setting and storage anchor named here
- [`../sse-event-bus/README.md`](../sse-event-bus/README.md) — why queries stream and uploads do not
- [`../api/knowledge-base.md`](../api/knowledge-base.md) — the five HTTP routes in full
- [`../rag-pipeline/README.md`](../rag-pipeline/README.md) — the eight-node pipeline that reads the corpus
- [`../../../Frontend/Documentation/knowledge-base/README.md`](../../../Frontend/Documentation/knowledge-base/README.md) — the upload UI in front of this path, and why its duplicate check asks a different question
