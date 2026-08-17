<div align="center">

# 💾 Storage Model

### Four persistent stores, four different formats, one directory — and no transaction holding any of them together.

<br>

[![Stores](https://img.shields.io/badge/persistent%20stores-4-1c7ed6)](#-3-four-stores-four-persistence-models)
[![Transactions](https://img.shields.io/badge/transactions-none-ef4444)](#-5-store-lifecycle)
[![Version](https://img.shields.io/badge/version-0.1.0-3fb950)](../../pyproject.toml)

[![Anchoring](https://img.shields.io/badge/DATA__ROOT-package--anchored-3fb950)](#-1-anchoring--the-bug-this-design-prevents)
[![Locks](https://img.shields.io/badge/locks-registry%20only-f59e0b)](#-3-four-stores-four-persistence-models)
[![Human-readable](https://img.shields.io/badge/human--readable-1%20of%204-f59e0b)](#-4-the-registry-entry)

</div>

<br>

---

<br>

## Content Tree

<pre>
Storage Model
│
├── <a href="#-overview">📖 Overview</a>
│
├── <a href="#-1-anchoring--the-bug-this-design-prevents">🧭 1. Anchoring — the bug this design prevents</a>
│   ├── <a href="#11-how-data_root-resolves">1.1 How DATA_ROOT resolves</a>
│   ├── <a href="#12-two-surviving-ways-to-break-it">1.2 Two surviving ways to break it</a>
│   └── <a href="#13-the-dependency-chain-and-what-cannot-be-moved">1.3 The dependency chain, and what cannot be moved</a>
│
├── <a href="#-2-what-is-actually-on-disk">📂 2. What is actually on disk</a>
│
├── <a href="#-3-four-stores-four-persistence-models">🧱 3. Four stores, four persistence models</a>
│   ├── <a href="#31-the-comparison">3.1 The comparison</a>
│   ├── <a href="#32-the-faiss-pickle-is-not-self-contained">3.2 The FAISS pickle is not self-contained</a>
│   ├── <a href="#33-graph-ingest-is-quadratic-in-disk-writes">3.3 Graph ingest is quadratic in disk writes</a>
│   └── <a href="#34-corruption-is-asymmetric-and-silent">3.4 Corruption is asymmetric and silent</a>
│
├── <a href="#-4-the-registry-entry">📄 4. The registry entry</a>
│
├── <a href="#-5-store-lifecycle">🔄 5. Store lifecycle</a>
│
├── <a href="#-6-operations--backup-move-reset">🧰 6. Operations — backup, move, reset</a>
│
├── <a href="#%EF%B8%8F-7-edge-cases--gotchas">⚠️ 7. Edge cases &amp; gotchas</a>
│
├── <a href="#-8-failure-modes">💥 8. Failure modes</a>
│
└── <a href="#-9-related-reading">🔗 9. Related reading</a>
</pre>

<br>

---

<br>

## 📖 Overview

Everything the backend persists lives under one directory, `Backend/data/`, and it is **git-ignored** —
nothing here travels with a clone. Inside it are two halves: the raw uploaded files exactly as the user
sent them, and four indexes built from those files.

The four indexes use four different persistence models. Chroma keeps a SQLite database plus binary HNSW
files and writes incrementally. BM25 and the entity graph each pickle their whole state on **every**
write. The knowledge-base registry is a JSON file with an `indent=2` and the only `threading.Lock` in
the backend. There is **no transaction across any of them**.

> [!IMPORTANT]
> **An ingest writes to four independent targets, in a fixed order, with nothing holding them
> together.** A crash between two of those writes leaves a document present in some stores and absent
> from others, and — if the registry write is the one that did not happen — invisible to the UI that
> would let you delete it. There is no rollback, no consistency check, and no repair command. The
> recovery path is `DELETE /api/clear`.

The directory layout is decided at import, once, by `Config` (§1). Where you started the process no
longer influences it — that was a real bug and the design that prevents it is the first thing this page
covers.

---

## 🧭 1. ANCHORING — THE BUG THIS DESIGN PREVENTS

### 1.1 How `DATA_ROOT` resolves

```python
# adrag/config.py:12-17
_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent   # adrag/ → src/ → Backend/
load_dotenv(_BACKEND_ROOT / ".env")                             # :19
DATA_ROOT: str = os.getenv("DATA_ROOT", str(_BACKEND_ROOT / "data"))   # :52
```

The default is computed from `__file__` and walked up three levels, so it is an **absolute path anchored
to the package**. Measured this run with no `.env` present, `Config.DATA_ROOT` resolves to
`…\Advanced RAG System\Backend\data` **regardless of the process working directory**.

The eight-line comment above that code records the retired behaviour verbatim: `DATA_ROOT` used to
default to `"./data"` against the working directory while the app started inside `src/`, *"which is how
the live stores ended up in `src/data/`."* Two `.gitignore` entries — `Backend/src/data/` and
`Backend/data/` (`:33-34`) — still cover both, the first now a leftover guard.

### 1.2 Two surviving ways to break it

**1 — a relative `DATA_ROOT` in `.env` is used verbatim**, and *is* resolved against the working
directory, reintroducing exactly the retired bug. `config.py:50-51` says so in a comment. Always set an
absolute path.

**2 — uncommenting a child without its parent.** python-dotenv interpolates `${DATA_ROOT}` against
variables already defined, so a `.env` with `DATA_ROOT` still commented out and
`UPLOAD_FOLDER=${DATA_ROOT}/uploads` uncommented expands to the literal `/uploads` — **the filesystem
root**.

```bash
# .env — WRONG
# DATA_ROOT=/absolute/path/to/data      ← still commented
UPLOAD_FOLDER=${DATA_ROOT}/uploads      ← expands to "/uploads"
```

This is why `.env.example` ships its **entire** storage block commented out (`:26-56`), with the warning
at `:34-35`. Uncomment the parent and the children together, or leave the whole block alone.

### 1.3 The dependency chain, and what cannot be moved

The chain is two levels deep:

```text
DATA_ROOT
├── UPLOAD_FOLDER          →  the raw files
└── DATABASE_ROOT
    ├── VECTOR_ROOT        →  CHROMA_PATH · FAISS_PATH
    ├── KEYWORD_ROOT       →  BM25_PATH
    ├── GRAPH_ROOT         →  GRAPH_PATH
    └── KB_REGISTRY_PATH   →  kb_registry.json
```

**`VECTOR_ROOT`, `GRAPH_ROOT` and `KEYWORD_ROOT` read no environment variable at all**
(`config.py:56-58`). You can relocate the whole tree by setting `DATA_ROOT` or `DATABASE_ROOT`, and you
can relocate an individual leaf by setting `CHROMA_PATH`, `BM25_PATH`, `GRAPH_PATH` or `FAISS_PATH` —
but you **cannot** relocate one retrieval kind's intermediate folder, because there is no variable
behind it.

`KB_REGISTRY_PATH` is the one setting read **outside `Config`** — `ingestion/registry.py:15` reads it
directly, defaulting to `${DATABASE_ROOT}/kb_registry.json`. Full details in
[`../configuration.md`](../configuration.md#61-tunable-but-not-a-config-attribute).

> [!NOTE]
> **One cwd-dependent behaviour survives, and it runs at import.** `registry.py:18-21` moves
> `./data/kb_registry.json` to the configured registry path when the old path exists and the new one does
> not — a legacy migration resolved against the *process working directory*. It only fires for a process
> started in a directory that still has the retired layout, but it is the last place where "where you
> started" changes what happens.

---

## 📂 2. WHAT IS ACTUALLY ON DISK

Read from the live tree this run.

```text
Backend/data/                                   ← gitignored (.gitignore:33-34)
├── 📁 uploads/                                 ← Config.UPLOAD_FOLDER — raw files, byte-for-byte
│   └── 📄 adrag-smoke-test.txt                    (the only file present right now)
└── 📁 databases/                               ← Config.DATABASE_ROOT
    ├── 📄 kb_registry.json                     ← KB_REGISTRY_PATH — the ONLY human-readable store
    ├── 📁 vector_db/                           ← Config.VECTOR_ROOT (no env var)
    │   └── 📁 chroma_db/                       ← Config.CHROMA_PATH
    │       ├── 📄 chroma.sqlite3                  Chroma's own SQLite database
    │       └── 📁 ebce24ab-45bb-…-19d724d85b6e/   the collection's HNSW binaries
    ├── 📁 keyword_db/bm25_store/bm25_store.pkl ← Config.BM25_PATH   — pickle
    └── 📁 graph_db/graph_store/graph_store.pkl ← Config.GRAPH_PATH  — pickle
```

`faiss_db/` is **absent** because `VECTOR_BACKEND=chroma`; it is created only on the opt-in path
(`pip install -e ".[faiss]"` plus `VECTOR_BACKEND=faiss`).

**Every one of those directories is created at import**, before any request exists — three by the store
modules at module scope and one by the factory. That is covered in
[`README.md`](README.md#32-importing-the-package-writes-to-disk).

> [!NOTE]
> **`.gitignore:30-32`'s comment is stale.** It explains the two data entries by saying *"DATA_ROOT
> (`./data`) resolves against the process working directory, and both main.py and dev.py start the app
> inside `Backend/src/`."* That is the retired behaviour (§1.1). **The ignore entries themselves are
> still correct** — only the rationale is out of date.

---

## 🧱 3. FOUR STORES, FOUR PERSISTENCE MODELS

### 3.1 The comparison

| | **Vector (Chroma)** | **Vector (FAISS)** | **BM25** | **Graph** | **Registry** |
|---|---|---|---|---|---|
| Format | SQLite + HNSW binaries | pickle **+ a sibling `.idx`** | **pickle** | **pickle** | **JSON**, `indent=2` |
| Written by | Chroma itself, incrementally | `_save()` on every write | `_save()` on every write | `_save()` on **every `add_document`** | `_save()` under a lock |
| What is stored | Chroma's own schema | `ids`, `documents`, `metadatas`, **a path pointer to `index_file`** | `{"corpus": [...], "metadatas": [...]}` — **the `BM25Okapi` object is not pickled**, it is rebuilt on load | `{"graph": nx.Graph, "doc_store": {...}}` | one object keyed by `file_hash` |
| Write amplification | none — incremental | full re-embed + rebuild on delete | full re-tokenise + `BM25Okapi` rebuild per write | **one full pickle dump per chunk** | one read + one write per operation |
| Load failure | **no handler — Chroma raises** | bare `except` → resets to empty (`vector_store.py:148-154`) | bare `except` → resets to empty (`bm25_store.py:61-63`) | bare `except` → resets to empty (`graph_store.py:180-182`) | bare `except` → returns `{}` (`registry.py:30-31`) |
| Lock | none | none | none | none | **`threading.Lock`** (`registry.py:22`) |

Three consequences follow directly from that table, and each is a live operational hazard rather than a
curiosity. How each store *searches* is a separate subject —
[`../hybrid-retrieval/stores.md`](../hybrid-retrieval/stores.md#-6-persistence) covers the internals.

### 3.2 The FAISS pickle is not self-contained

The FAISS backend writes two files: a pickle of the documents and metadata, and a binary index written
by `faiss.write_index`. **The pickle stores a path to that sibling file** (`vector_store.py:158-169`),
not its contents.

**So moving the data directory breaks a FAISS index even though the pickle came along**, because the
stored path no longer points anywhere. Chroma has no equivalent problem — its SQLite database and HNSW
directory are relative to the collection folder.

### 3.3 Graph ingest is quadratic in disk writes

`graph_store.add_document` ends with `self._save()` (`graph_store.py:85`), and
`services.py:65-66` calls it **once per chunk**. A 200-chunk PDF therefore performs **200 full pickle
dumps of a graph that grows with every one of them** — the dominant disk cost of ingestion, and the
reason a large document feels slow long after the embeddings are done.

The write path and its ordering are documented in
[`../ingestion/README.md`](../ingestion/README.md#41-the-write-path-end-to-end).

### 3.4 Corruption is asymmetric and silent

Three of the five loaders swallow **every** exception and reset to empty; the default vector backend
does not.

> [!CAUTION]
> **A corrupt `bm25_store.pkl` silently empties keyword search while vector search keeps working — with
> no log line, no exception and no warning.** The next write then persists the emptiness. Because Chroma
> (the default) has *no* such handler and raises instead, the failure modes of the two stores are
> opposite: one fails loudly at startup, the other quietly degrades the corpus. Do not assume a
> consistent behaviour across the four.

The same shape applies to the registry, and there it is worse — see §8.

---

## 📄 4. THE REGISTRY ENTRY

`kb_registry.json` is the only store a human can open and read. One entry per `file_hash`
(`registry.py:45-53`):

```json
{
  "a3f8c2e1…": {
    "id":          "a3f8c2e1…",
    "name":        "my_document.pdf",
    "uploaded_at": "2026-08-16T10:30:00+00:00",
    "chunks":      42,
    "vectors":     42,
    "entities":    18,
    "edges":       27
  }
}
```

| Field | What it really is |
|---|---|
| `id` | **the key, and the MD5 of the file's *content***, not of its name (`loader.py:48-54`). Two identical files uploaded under different names collide here deliberately — that is the dedup mechanism. |
| `name` | the sanitised filename as saved, so it may differ from what the user chose (§8, and [`../api/knowledge-base.md`](../api/knowledge-base.md#26-filename-sanitisation-and-what-it-costs)) |
| `uploaded_at` | `datetime.now(timezone.utc).isoformat()` (`registry.py:48`) — **refreshed on re-index**, so it is a *last indexed* time, not a first upload time |
| `chunks` | the number of text chunks produced |
| `vectors` | simply `len(texts)` — one chunk, one embedding (`services.py:71`) |
| `entities` | **per file** — the entities extracted from this document |
| `edges` | ⚠️ **the WHOLE graph's total**, not this file's (`services.py:72-73` versus `graph_store.py:159`) |

> [!WARNING]
> **`edges` is the same number in every row.** It reports the global edge count at the moment that entry
> was written, so a knowledge base's row tells you nothing about its own edge contribution and rows
> written at different times disagree with each other. Read it as a snapshot of the graph, not a property
> of the document.

The registry is also **the only component in the backend with explicit thread synchronisation** — a
`threading.Lock` held across each read-modify-write (`registry.py:22`, held at `:43`, `:61`, `:67`,
`:76`, `:86`). Nothing protects the three stores.

---

## 🔄 5. STORE LIFECYCLE

| Moment | What happens |
|---|---|
| **import** | directories created; the BM25 and graph pickles are read; the Chroma client is opened and its collection created if absent |
| **first embed or search** | `SentenceTransformer` weights loaded (`embeddings.py:16-21`) |
| **first rerank** | `CrossEncoder` weights loaded (`reranker.py:23-31`) |
| **every ingest** | `remove_document(hash)` first, then all three stores and the registry, in fixed order, **with no transaction** |
| **every delete** | the same four, same order — and **all four return values are discarded** (`services.py:86-91`), so a delete can never report "not found" |
| **`DELETE /api/clear`** | all three stores, `registry.clear_all()`, then a loop deleting the uploaded file **named by each registry entry** |
| **shutdown** | nothing. No flush, no close, no `atexit` — every write already went to disk |

**Dedup is delete-then-add, never upsert.** Re-uploading the same content removes the prior copy from all
three stores and re-indexes it, which is why `uploaded_at` refreshes and why the operation costs as much
as a first ingest.

Nothing here is encrypted, checksummed or versioned: plain files, plain pickles, plain JSON, plain
SQLite.

---

## 🧰 6. OPERATIONS — BACKUP, MOVE, RESET

| Question | The answer, from the code |
|---|---|
| **How do I back this up?** | Copy `Backend/data/` while the server is stopped. There is no export endpoint and no snapshot API. |
| **How do I reset everything?** | `DELETE /api/clear`, **or** stop the server and delete `Backend/data/databases/`. The directories are recreated at the next import. |
| **What does `DELETE /api/clear` not remove?** | Uploaded files **not named by a registry entry** — orphans from a failed ingest. They accumulate permanently (`services.py:96-104`). |
| **Can I move the data?** | Yes, via an **absolute** `DATA_ROOT` in `.env` — but a FAISS index breaks, because its pickle stores a path to the sibling `.idx` (§3.2). |
| **Does switching `VECTOR_BACKEND` migrate anything?** | **No.** It silently exposes a different, probably empty index. `.env.example:59` says so. |
| **Is anything encrypted or checksummed?** | No. |
| **What survives a `Ctrl-C` mid-ingest?** | Whatever was already written. No transaction, no rollback — see §8. |

**Moving the data safely, in order:** stop the server → copy `Backend/data/` to the new location → set an
absolute `DATA_ROOT` in `Backend/.env` (uncommenting the *whole* storage block, §1.2) → restart → confirm
with `GET /api/documents` that the counts match what you had.

---

## ⚠️ 7. EDGE CASES & GOTCHAS

- **Import creates directories even in a REPL.** `import adrag.app` is enough to materialise the whole
  tree, because the store singletons are constructed at module scope. There is no read-only mode.

- **`VECTOR_BACKEND` is read once, at import.** Switching it does not migrate, does not warn, and does
  not touch the old index — it simply points the application at a different one.

- **The BM25 index is rebuilt, not loaded.** Only the corpus and metadata are pickled; the `BM25Okapi`
  object is reconstructed on load, so load time grows with corpus size and a version change in
  `rank-bm25` affects behaviour without touching the file.

- **A delete's return value is thrown away four times over.** `services.py:86-91` ignores all four, so
  deleting a `file_hash` that does not exist succeeds silently.

- **Orphaned uploads are never reclaimed.** `clear_everything` only deletes files a registry entry names.
  A file saved by an ingest that then failed is invisible to every code path in the system.

- **Nothing bounds `UPLOAD_FOLDER`.** No quota, no retention, no cleanup job. The only size control
  anywhere is Flask's 50 MB per-request `MAX_CONTENT_LENGTH`.

- **Concurrent ingest is unsafe.** The three stores are unsynchronised module singletons; only the
  registry has a lock. Two simultaneous uploads can interleave their pickle writes and lose one of them
  entirely.

---

## 💥 8. FAILURE MODES

| Failure | Mechanism | Blast radius |
|---|---|---|
| **A corrupt `kb_registry.json` wipes every other record** | `registry._load()` (`:25-32`) catches every exception and returns `{}`; `register()` then does `data = _load()` → `data[hash] = entry` → `_save(data)` (`:44-55`) | **One unreadable registry plus one subsequent upload permanently discards every other record**, while all three stores still hold their chunks. The corpus becomes searchable but unlistable and undeletable through the UI. |
| **A corrupt pickle silently empties a store** | bare `except` → reset to empty (`bm25_store.py:61-63`, `graph_store.py:180-182`, `vector_store.py:148-154`); the next write persists the emptiness | Total, silent loss of that store. No log line, no exception, no warning. Chroma is unaffected — it has no such handler. |
| **A crash between two of the four writes** | `services.py:6-9` states the absence of a transaction outright | A document searchable by keyword and vector, invisible to the graph, and **absent from the registry — so there is no UI path to delete it.** Only `DELETE /api/clear` recovers. |
| **A failed ingest orphans its file** | neither `except` branch removes `file_path` (`knowledge_base_routes.py:64-67`) | Orphans accumulate in `UPLOAD_FOLDER` permanently. |
| **Moving `data/` with a FAISS index** | the pickle stores a path to the `.idx` (`vector_store.py:158-169`) | The index fails to resolve at load. Chroma is unaffected. |
| **`VECTOR_BACKEND` flipped on a populated install** | import-time class selection (`vector_store.py:250-253`) | Search returns nothing; the old index is intact but unreachable until the variable is flipped back. |
| **FAISS only — deleting the last file** | `vector_store.py:227` raises `ValueError` on an empty index; BM25 guards the same case at `bm25_store.py:95-98` | The delete fails on the FAISS path where it succeeds on every other. |

> [!CAUTION]
> **The registry failure is the one to design around.** Every other corruption loses one store's data.
> A corrupt registry loses the *ability to manage* all of them: the chunks stay searchable, but the UI
> can no longer list or delete the documents they came from, and the next upload makes the loss
> permanent. If you back up nothing else, back up `kb_registry.json`.

---

## 🔗 9. RELATED READING

- **Why embedded, file-backed stores.** No server to run, no container, no credentials, no network hop —
  a single-machine tool that a reader can clone and start. The price is everything on this page: no
  transactions, no concurrent writers, no migrations, and corruption handling that varies per store.
- **Why pickle for two of them.** `BM25Okapi` and a NetworkX graph have no obvious serialised form, and
  pickle made them persist in three lines each. The cost is a format that is version-fragile, opaque to
  inspection, and a deserialisation surface worth understanding before `data/` is ever shared between
  machines — see [`../security.md`](../security.md#-8-pickle-load-as-a-deserialisation-surface).
- **Why the registry exists at all.** The three stores can answer *what matches this query* but none can
  answer *what documents do I have*. The registry is the index over the indexes, which is exactly why
  losing it is worse than losing any single store.
- **Why anchoring is written down so emphatically.** The retired cwd-relative default did not fail — it
  silently created a second, empty corpus wherever the process happened to start. A bug that produces no
  error and looks like data loss is worth a comment block and a warning in every doc that touches it.

**Continue reading:**

- [`README.md`](README.md) — the boot sequence that creates all of this, and the one-worker rule
- [`query-lifecycle.md`](query-lifecycle.md) — the read path these stores serve
- [`../ingestion/README.md`](../ingestion/README.md) — who writes each store, in what order, and what a duplicate does
- [`../hybrid-retrieval/stores.md`](../hybrid-retrieval/stores.md) — how each store indexes, searches and scores
- [`../configuration.md`](../configuration.md) — every path setting and its real default
- [`../api/knowledge-base.md`](../api/knowledge-base.md) — the routes that trigger every write on this page
- [`../security.md`](../security.md) — the deserialisation surface and the data-integrity risks
