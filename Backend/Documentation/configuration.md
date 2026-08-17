<div align="center">

# ⚙️ Configuration

### Every setting the backend reads — its real default, where it is cast, what it moves, and the four ways the convention is broken.

<br>

[![Config attributes](https://img.shields.io/badge/Config%20attributes-29-1c7ed6)](#-2-the-complete-config-reference)
[![Env-backed](https://img.shields.io/badge/env--backed-24-7c5cff)](#-2-the-complete-config-reference)
[![Version](https://img.shields.io/badge/version-0.1.0-3fb950)](../pyproject.toml)

[![Template](https://img.shields.io/badge/template-.env.example-f59e0b)](../.env.example)
[![Frozen](https://img.shields.io/badge/read-once%20at%20import-f59e0b)](#-1-how-a-setting-resolves)

</div>

<br>

---

<br>

## Content Tree

<pre>
Configuration
│
├── <a href="#-overview">📖 Overview</a>
│
├── <a href="#-1-how-a-setting-resolves">🧭 1. How a setting resolves</a>
│   ├── <a href="#11-precedence-top-wins">1.1 Precedence, top wins</a>
│   └── <a href="#12-everything-is-read-once-at-import">1.2 Everything is read once, at import</a>
│
├── <a href="#-2-the-complete-config-reference">📋 2. The complete Config reference</a>
│   └── <a href="#21-the-four-rows-that-need-their-own-warning">2.1 The four rows that need their own warning</a>
│
├── <a href="#-3-the-storage-tree">💾 3. The storage tree</a>
│   ├── <a href="#31-what-is-on-disk">3.1 What is on disk</a>
│   ├── <a href="#32-break-1--a-relative-data_root">3.2 Break #1 — a relative DATA_ROOT</a>
│   └── <a href="#33-break-2--uncommenting-a-child-without-its-parent">3.3 Break #2 — uncommenting a child without its parent</a>
│
├── <a href="#-4-where-the-template-and-the-code-disagree">🔀 4. Where the template and the code disagree</a>
│
├── <a href="#-5-the-duplicated-default-pattern">🧬 5. The duplicated-default pattern</a>
│
├── <a href="#-6-settings-that-live-outside-config">🚫 6. Settings that live outside Config</a>
│   ├── <a href="#61-tunable-but-not-a-config-attribute">6.1 Tunable, but not a Config attribute</a>
│   ├── <a href="#62-hardcoded-constants">6.2 Hardcoded constants</a>
│   └── <a href="#63-settings-belonging-to-the-other-halves">6.3 Settings belonging to the other halves</a>
│
├── <a href="#-7-how-config-reaches-flask">🔒 7. How Config reaches Flask</a>
│
├── <a href="#-8-changing-a-setting-safely">🧩 8. Changing a setting safely</a>
│
└── <a href="#-9-known-drift--deeper-reading">🔗 9. Known drift &amp; deeper reading</a>
</pre>

<br>

---

<br>

## 📖 Overview

The backend's configuration is one class of plain attributes — `Config` in
[`Backend/src/adrag/config.py`](../src/adrag/config.py), 77 lines — plus a template,
[`Backend/.env.example`](../.env.example), that you copy to `.env` and edit. There is no configuration
framework, no schema, no validation, and no per-environment file: every value is
`os.getenv("NAME", "<literal default>")` with the cast applied immediately at the call site.

The stated convention is that **a setting is a `Config` attribute *and* a documented `.env.example`
line.** Four distinct kinds of exception to that rule exist in the current code, and this page
enumerates all of them rather than leaving them to be discovered one at a time.

> [!IMPORTANT]
> **`DATA_ROOT` is anchored to the package, not to the working directory — and must stay that way.**
> `config.py:17` computes `_BACKEND_ROOT` from `__file__` (`adrag/` → `src/` → `Backend/`) and defaults
> every data path against it, so **where you start the server no longer decides where the databases
> land.** It used to: `DATA_ROOT` defaulted to `"./data"` against the process working directory while
> the app started inside `src/`, which is how the live stores once ended up in `Backend/src/data/`.
> Reintroducing a relative default reintroduces the bug — and a relative value set in `.env` still can
> (§3.2).

---

## 🧭 1. HOW A SETTING RESOLVES

### 1.1 Precedence, top wins

```python
# Backend/src/adrag/config.py:17
_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent

load_dotenv(_BACKEND_ROOT / ".env")
```

| Rank | Source | Notes |
|---|---|---|
| 1 | the **process environment** | a shell export, a systemd unit, a parent process — **beats the file** |
| 2 | `Backend/.env` | loaded from an **explicit absolute path**, so it is found no matter where the process started |
| 3 | the literal default in `config.py` | the value in the `os.getenv(...)` call itself |

**The process environment winning is not an accident, and something depends on it.**
`load_dotenv`'s `override` parameter defaults to `False`, and `config.py:19` does not pass it — so an
already-set variable is left alone. `infra/dev.py:265-269` relies on exactly that: it injects `PORT` and
`FRONTEND_URL` into the child process environment precisely because they take precedence over whatever
`.env` says, which is how it can hand the backend a port it probed for at runtime.

The same mechanism is how the OpenAI credential reaches the SDK — see
[`llm-providers/README.md`](llm-providers/README.md) §4.3.

### 1.2 Everything is read once, at import

`Config` is a class of **plain class attributes evaluated once, at class-definition time**. There is no
`__init__`, no reload, and no per-request read. Two consequences:

- **Editing `.env` while the server runs changes nothing.** Not the model, not the port, not a path.
  Restart the process.
- **Derived paths are resolved in the class body.** `UPLOAD_FOLDER`'s default reads `DATA_ROOT` as a
  local at definition time (`config.py:53`), so the whole `DATA_ROOT → DATABASE_ROOT → VECTOR_ROOT →
  CHROMA_PATH` chain collapses to concrete strings at import and never re-derives.

The same is true of every setting read *outside* `Config` — the pipeline nodes read theirs with
`os.getenv` at **module scope** (§5), which is import time as well. Nothing in this backend re-reads the
environment per request, which is consistent with the LLM instance cache that is never invalidated.

---

## 📋 2. THE COMPLETE `Config` REFERENCE

All 29 attributes, in source order. **24 read an environment variable; 5 do not.**

| # | Attribute | Line | Env var | Default | Cast |
|---|---|---|---|---|---|
| 1 | `OPENAI_API_KEY` | `:24` | `OPENAI_API_KEY` | `""` | `str` |
| 2 | `LLM_MODEL` | `:25` | `LLM_MODEL` | `gpt-4o-mini` | `str` |
| 3 | `OLLAMA_BASE_URL` | `:28` | `OLLAMA_BASE_URL` | `http://localhost:11434` | `str` |
| 4 | `OLLAMA_MODEL` | `:29` | `OLLAMA_MODEL` | `llama3.2` | `str` |
| 5 | `DEFAULT_PROVIDER` | `:32` | `DEFAULT_PROVIDER` | `openai` | `str` |
| 6 | `EMBEDDING_MODEL` | `:35` | `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | `str` |
| 7 | `RERANKER_MODEL` | `:36` | `RERANKER_MODEL` | `cross-encoder/ms-marco-MiniLM-L-6-v2` | `str` |
| 8 | `RETRIEVAL_TOP_K` | `:39` | `RETRIEVAL_TOP_K` | `10` | `int()` |
| 9 | `RERANK_TOP_K` | `:40` | `RERANK_TOP_K` | `5` | `int()` |
| 10 | `MAX_CONTEXT_CHARS` | `:41` | `MAX_CONTEXT_CHARS` | `4000` | `int()` |
| 11 | `MAX_REFLECTION_RETRIES` | `:42` | `MAX_REFLECTION_RETRIES` | `2` | `int()` |
| 12 | `CHUNK_SIZE` | `:45` | `CHUNK_SIZE` | `500` | `int()` |
| 13 | `CHUNK_OVERLAP` | `:46` | `CHUNK_OVERLAP` | `50` | `int()` |
| 14 | `DATA_ROOT` | `:52` | `DATA_ROOT` | `_BACKEND_ROOT / "data"` → `Backend/data` | `str` |
| 15 | `UPLOAD_FOLDER` | `:53` | `UPLOAD_FOLDER` | `{DATA_ROOT}/uploads` | `str` |
| 16 | `DATABASE_ROOT` | `:54` | `DATABASE_ROOT` | `{DATA_ROOT}/databases` | `str` |
| 17 | `VECTOR_ROOT` | `:56` | **none** | `{DATABASE_ROOT}/vector_db` | `str` |
| 18 | `GRAPH_ROOT` | `:57` | **none** | `{DATABASE_ROOT}/graph_db` | `str` |
| 19 | `KEYWORD_ROOT` | `:58` | **none** | `{DATABASE_ROOT}/keyword_db` | `str` |
| 20 | `CHROMA_PATH` | `:60` | `CHROMA_PATH` | `{VECTOR_ROOT}/chroma_db` | `str` |
| 21 | `FAISS_PATH` | `:61` | `FAISS_PATH` | `{VECTOR_ROOT}/faiss_db` | `str` |
| 22 | `GRAPH_PATH` | `:62` | `GRAPH_PATH` | `{GRAPH_ROOT}/graph_store/graph_store.pkl` | `str` |
| 23 | `BM25_PATH` | `:63` | `BM25_PATH` | `{KEYWORD_ROOT}/bm25_store/bm25_store.pkl` | `str` |
| 24 | `VECTOR_BACKEND` | `:66` | `VECTOR_BACKEND` | `chroma`, **`.lower()`-ed** | `str` |
| 25 | `MAX_CONTENT_LENGTH` | `:69` | **none** | `50 * 1024 * 1024` (50 MB) | `int` |
| 26 | `ALLOWED_EXTENSIONS` | `:70-73` | **none** | a 35-entry `set` | `set` |
| 27 | `FRONTEND_URL` | `:75` | `FRONTEND_URL` | `http://localhost:8080` | `str` |
| 28 | `DEBUG` | `:76` | **`FLASK_DEBUG`** ⚠️ | `true` → `True` | `.lower() == "true"` |
| 29 | `PORT` | `:77` | `PORT` | `5000` | `int()` |

### 2.1 The four rows that need their own warning

> [!WARNING]
> **`DEBUG` is the one attribute whose name differs from its environment variable.** It reads
> **`FLASK_DEBUG`** (`config.py:76`). Setting `DEBUG=false` in `.env` changes **nothing** — the Werkzeug
> debugger stays on, and with it an interactive code-execution console on any reachable port. The
> truthiness test is a literal string compare (`.lower() == "true"`), so `False`, `0` and `no` all
> evaluate to `False` — and so does any typo, which at least fails safe.

**`VECTOR_ROOT` / `GRAPH_ROOT` / `KEYWORD_ROOT` read no environment variable at all** (`config.py:56-58`).
They are pure derivations of `DATABASE_ROOT`. You can move the whole database tree (`DATABASE_ROOT`) or
an individual leaf (`CHROMA_PATH`, `BM25_PATH`, `GRAPH_PATH`, `FAISS_PATH`), but **you cannot move one
retrieval kind's folder** — there is no variable for it. `.env.example:43-48` documents that tree as
prose comments precisely because there is nothing to set.

**`MAX_CONTENT_LENGTH` is a real, enforced limit, and it breaks the JSON error contract.**
`app.py:35` calls `app.config.from_object(Config)`, Flask picks up every uppercase attribute, and
Werkzeug rejects any request body over 50 MB before a route runs. **No `errorhandler` is registered
anywhere in the backend**, so the client gets Werkzeug's default **HTML 413** rather than the
`{"error": …}` shape every other failure uses.

**`ALLOWED_EXTENSIONS` is not environment-tunable and is duplicated by design.** It is exactly equal to
`loader.SUPPORTED_EXTENSIONS` (35 entries each), and adding a file type therefore means editing **two**
files in two packages. The reasoning is in [`ingestion/README.md`](ingestion/README.md) §5.1.

---

## 💾 3. THE STORAGE TREE

### 3.1 What is on disk

```text
Backend/data/                                          ← gitignored
├── uploads/                                           ← Config.UPLOAD_FOLDER; raw files, verbatim
└── databases/                                         ← Config.DATABASE_ROOT
    ├── kb_registry.json                               ← KB_REGISTRY_PATH (no Config attribute)
    ├── vector_db/                                     ← Config.VECTOR_ROOT
    │   └── chroma_db/                                 ← Config.CHROMA_PATH
    │       ├── chroma.sqlite3
    │       └── <collection-uuid>/                     binary index segments
    ├── keyword_db/bm25_store/bm25_store.pkl           ← Config.BM25_PATH
    └── graph_db/graph_store/graph_store.pkl           ← Config.GRAPH_PATH
```

`faiss_db/` is absent on a default install because `VECTOR_BACKEND=chroma`; it is created only on the
opt-in path. `Config.UPLOAD_FOLDER` is the one directory the application creates for itself, at factory
time (`app.py:49`).

> [!WARNING]
> **Switching `VECTOR_BACKEND` does not migrate data.** It silently exposes a different — and probably
> empty — index. The keyword and graph stores are untouched by the switch, so the corpus becomes
> internally inconsistent: BM25 and the graph still know about documents the vector store has never
> seen. See [`hybrid-retrieval/stores.md`](hybrid-retrieval/stores.md).

### 3.2 Break #1 — a relative `DATA_ROOT`

The default is absolute and package-anchored, but a value set in `.env` is used **verbatim** — the
comment at `config.py:50-51` says so. A relative value there *is* resolved against the process working
directory, which reintroduces exactly the bug `_BACKEND_ROOT` was added to kill: the databases land
wherever the server happened to start, and starting it from a different folder silently produces an
empty corpus.

**Prefer an absolute path.** This is why `.env.example` ships its entire storage block **commented out**
(`.env.example:26-56`) rather than shipping working-looking defaults.

### 3.3 Break #2 — uncommenting a child without its parent

`.env.example` documents each path with a `${DATA_ROOT}`-style reference, and python-dotenv performs
POSIX-style interpolation against variables **already defined**. So:

```bash
# .env — WRONG
# DATA_ROOT=/absolute/path/to/data      ← still commented
UPLOAD_FOLDER=${DATA_ROOT}/uploads      ← expands to "/uploads"
```

The prefix expands to the **empty string**, and `UPLOAD_FOLDER` becomes the literal `/uploads` — the
filesystem root, not a folder under `Backend/`. `.env.example:34-35` states this in exactly those terms.

**The dependency is two levels deep:**

```text
DATA_ROOT ─┬─ UPLOAD_FOLDER
           └─ DATABASE_ROOT ─┬─ VECTOR_ROOT ─┬─ CHROMA_PATH
                             │               └─ FAISS_PATH
                             ├─ GRAPH_ROOT ──── GRAPH_PATH
                             └─ KEYWORD_ROOT ── BM25_PATH
```

**Uncomment a parent and you must uncomment every child that references it — or leave the whole block
commented.** Half-measures do not fail loudly; they produce paths that are syntactically fine and
point somewhere nobody intended.

---

## 🔀 4. WHERE THE TEMPLATE AND THE CODE DISAGREE

`Backend/.env.example` is 66 lines in six sections. Diffed line by line against the 29 attributes above,
in **both** directions:

**A · In `config.py`, absent from `.env.example` — 2 settings.**

| Setting | `Config` | Also read at | Effect |
|---|---|---|---|
| `CHUNK_SIZE` | `config.py:45` | `loader.py:24` | **Works, but is undiscoverable** |
| `CHUNK_OVERLAP` | `config.py:46` | `loader.py:25` | Same |

> [!IMPORTANT]
> **There is no chunking section in `.env.example` at all** — grepping it for `CHUNK` returns nothing.
> Both settings are genuinely honoured, because `loader.py` reads the environment directly, so putting
> them in `.env` really does change how documents are split. A reader simply has no way to learn they
> exist except by reading `config.py`. **This is the single most actionable gap in the configuration
> surface.** Note also that changing them requires a **re-index** as well as a restart: existing chunks
> keep the size they were written at.

**B · In `.env.example`, not a `Config` attribute — 1 setting.**

| Setting | Read at | In the template | Effect |
|---|---|---|---|
| `KB_REGISTRY_PATH` | `registry.py:15` | `:54-56`, commented, **with a note saying it is read directly rather than through `Config`** | Discoverable and honest, but it breaks the convention |

**C · Present in both, values disagree — 1 setting.**

| Setting | `config.py` | `.env.example` | Verdict |
|---|---|---|---|
| `OLLAMA_MODEL` | `llama3.2` (`:29`, and `llm.py:53`) | `llama3.2:latest` (`:11`) | **Cosmetic.** Ollama resolves an untagged name to `:latest`, so both select the same model — but the two strings are not equal, which matters to anything that compares them |

**D · Everything else agrees.** Of the 24 environment-backed attributes, 22 appear in `.env.example`
(the two absentees are in group A), and 21 of those 22 carry identical defaults (the exception is group
C). `OPENAI_API_KEY` is counted as matching even though the two strings differ: the template ships the
fill-in placeholder `sk-...` against a `Config` default of `""`, and that is a prompt to supply a
secret, not a competing default. The five non-environment attributes — `VECTOR_ROOT`, `GRAPH_ROOT`,
`KEYWORD_ROOT`, `MAX_CONTENT_LENGTH`, `ALLOWED_EXTENSIONS` — are **not omissions**: they read no
variable, so there is nothing to document as a `.env` line. Saying so explicitly matters, because a
reader scanning the template for them otherwise concludes there is a gap.

---

## 🧬 5. THE DUPLICATED-DEFAULT PATTERN

**The pipeline nodes do not import `Config`.** Only the three stores and the registry do
(`vector_store.py:13`, `bm25_store.py:15`, `graph_store.py:17`, `registry.py:13`). Every node instead
calls `os.getenv(...)` at module scope with its **own literal copy** of the default. The full inventory
— **16 `os.getenv` calls outside `config.py`**:

| Env var | Duplicated at | Literal default there | Agrees with `Config`? |
|---|---|---|---|
| `CHUNK_SIZE` | `loader.py:24` | `"500"` | ✅ |
| `CHUNK_OVERLAP` | `loader.py:25` | `"50"` | ✅ |
| `EMBEDDING_MODEL` | `embeddings.py:11` | `all-MiniLM-L6-v2` | ✅ |
| `RETRIEVAL_TOP_K` | `hybrid_node.py:22` | `"10"` | ✅ |
| `RERANKER_MODEL` | `reranker.py:20` | `cross-encoder/ms-marco-MiniLM-L-6-v2` | ✅ |
| `RERANK_TOP_K` | `reranker.py:21` | `"5"` | ✅ |
| `MAX_CONTEXT_CHARS` | `compressor.py:20` | `"4000"` | ✅ |
| `MAX_REFLECTION_RETRIES` | `reflection.py:21` | `"2"` | ✅ |
| `MAX_REFLECTION_RETRIES` | `workflow.py:33` | `"2"` | ✅ — but the constant is **dead code** |
| `OLLAMA_MODEL` | `llm.py:53` | `llama3.2` | ✅ |
| `OLLAMA_BASE_URL` | `llm.py:54` | `http://localhost:11434` | ✅ |
| `LLM_MODEL` | `llm.py:62` | `gpt-4o-mini` | ✅ |
| `OLLAMA_BASE_URL` | `llm.py:110` | `http://localhost:11434` | ✅ |
| `KB_REGISTRY_PATH` | `registry.py:15` | `Config.DATABASE_ROOT/kb_registry.json` | n/a — see §6.1 |
| `BM25_PATH` | `bm25_store.py:17` | **`Config.BM25_PATH`** | ✅ — a *double read*, not a duplicate |
| `GRAPH_PATH` | `graph_store.py:19` | **`Config.GRAPH_PATH`** | ✅ — same |

**Three things to be precise about:**

1. **Every duplicated default currently agrees with `Config`.** This is a **maintenance hazard, not a
   live bug** — there is no divergence today. But changing a default in `config.py` alone would silently
   fail to reach the node that re-declares it, and nothing would report the mismatch.
2. **The two store modules use a better pattern.** `os.getenv("BM25_PATH", Config.BM25_PATH)` falls back
   to the `Config` attribute rather than to a literal. Since `Config.BM25_PATH` already reads the same
   variable, the outer `getenv` is redundant — but it **can never drift**. If this repository ever
   standardises on one pattern, this is the one to standardise on.
3. **All of these are module-scope reads, frozen at import** (§1.2). Nothing re-reads per request.

---

## 🚫 6. SETTINGS THAT LIVE OUTSIDE `Config`

### 6.1 Tunable, but not a `Config` attribute

**`KB_REGISTRY_PATH`** — read directly at `registry.py:15`:

```python
# custom_packages/rag_pipeline/ingestion/registry.py:15
_REGISTRY_PATH = os.getenv("KB_REGISTRY_PATH", os.path.join(Config.DATABASE_ROOT, "kb_registry.json"))
```

It is the **one setting in the backend that is not a `Config` attribute**. It is documented in
`.env.example:54-56` — with a comment that says exactly this — so it is discoverable rather than hidden,
but it still breaks the convention. Promote it to `Config` if you ever touch that file.

Note also that `registry.py:18-21` runs a **one-shot legacy migration at import**: if
`./data/kb_registry.json` exists relative to the working directory and the configured path does not, it
`shutil.move`s the file. That check runs on every import of the module.

### 6.2 Hardcoded constants

Not tunable at all — changing any of these means editing code:

| Constant | Value | Line | Caps |
|---|---|---|---|
| `_EVENT_TIMEOUT_SECONDS` | `180` | `query_routes.py:28` | the SSE per-event wait |
| `MAX_CONTENT_LENGTH` | 50 MB | `config.py:69` | the HTTP request body, enforced by Flask |
| `ALLOWED_EXTENSIONS` | 35 entries | `config.py:70-73` | which uploads the route accepts |
| `WEB_RESULTS` | `5` | `web_node.py:17` | DuckDuckGo results per escalation |
| `COLLECTION_NAME` | `"rag_documents"` | `vector_store.py` | the Chroma collection |
| LLM `temperature` | `0` | `llm.py:24` (signature default) | never passed by any call site |
| Graph traversal weights | `2.0` / `0.5` | `graph_store.py` | direct vs two-hop entity match |
| Compressor input cap | `10_000` chars | `compressor.py:79` | what the compression LLM can even see |
| Reflection context cap | `4000` chars | `reflection.py` | what the critic reads |
| Reasoning fallback caps | `3000` / `250` chars | `reasoning.py` | retry context, and the source preview |
| Web result score | `0.7` | `web_node.py` | a fixed, non-comparable placeholder |

### 6.3 Settings belonging to the other halves

Named here only so a reader searching for them does not conclude they are missing. **None of these is a
backend setting.**

| Variable | Read at | Scope |
|---|---|---|
| `NO_COLOR` | `infra/dev.py:52` | dev tooling only — suppresses ANSI colour |
| `DEV_API_TARGET` | `Frontend/vue.config.js:19` | set by `infra/dev.py:281`; retargets the dev-server `/api` proxy |
| `VUE_APP_API_URL` | `Frontend/src/services/ragApi.js:12`, and `kbApi.js` | frontend **build-time**; Vue CLI only exposes `VUE_APP_`-prefixed variables |

---

## 🔒 7. HOW `Config` REACHES FLASK

```python
# Backend/src/adrag/app.py:34
app = Flask(__name__)
app.config.from_object(Config)
```

Flask copies **every uppercase attribute** into `app.config`, so `MAX_CONTENT_LENGTH`, `DEBUG`,
`UPLOAD_FOLDER`, `ALLOWED_EXTENSIONS` and the rest all land there. Only **`MAX_CONTENT_LENGTH` and
`DEBUG`** are names Flask itself acts on; the application reads everything else off `Config` directly
rather than through `app.config`. **`SECRET_KEY` is never set** — no session or flash messaging is used,
so nothing depends on it today.

**CORS** is configured in the same factory (`app.py:37-47`) with an origins list of
`[Config.FRONTEND_URL, "http://localhost:3000", "http://localhost:5000", "http://localhost:8080",
"http://localhost:8081", "*"]`.

> [!CAUTION]
> **Three configuration defaults are, together, a remote compromise the moment the port is reachable
> off the machine.**
>
> 1. **The literal `"*"` in the CORS origins list makes the entire named allowlist decorative**
>    (`app.py:41`). Every origin is permitted, including the four localhost entries the list appears to
>    restrict it to.
> 2. **`FLASK_DEBUG` defaults to `true`** (`config.py:76`), leaving the Werkzeug interactive debugger
>    enabled — a code-execution console on the served port.
> 3. **No route carries authentication.** `DELETE /api/clear` wipes the entire index unauthenticated.
>
> These are documented, **localhost-only** accepted risks, not oversights to be worked around. Never
> expose this deployment beyond localhost without closing all three first. See
> [`security.md`](security.md#-11-before-this-leaves-localhost), where those three are items 1–3.

---

## 🧩 8. CHANGING A SETTING SAFELY

**Change an existing value.** Edit `Backend/.env` (copied from `.env.example`) and **restart** — nothing
is re-read at runtime (§1.2). If the value is not taking effect, check in this order: is it exported in
your shell (§1.1, the shell wins); is it `DEBUG` when the variable is `FLASK_DEBUG` (§2.1); is it a
storage path whose parent is still commented out (§3.3); does a node hold its own duplicate copy of the
default while you edited only `config.py` (§5).

**Add a new setting.** Two edits, always: a `Config` attribute with its cast at the call site
(`config.py`), **and** a documented line in `.env.example` in the matching section. If the value is also
needed inside the pipeline, prefer the store pattern — `os.getenv("NAME", Config.NAME)` — over a
re-declared literal (§5).

**Move the data directory.** Set `DATA_ROOT` to an **absolute** path and uncomment every child that
references it, or leave the whole block commented and let the package anchoring do its job. You cannot
relocate a single retrieval kind: `VECTOR_ROOT`, `GRAPH_ROOT` and `KEYWORD_ROOT` read nothing (§2.1).
Moving the directory does **not** move existing data — copy it yourself, or re-index.

**Change chunking.** `CHUNK_SIZE` / `CHUNK_OVERLAP` in `.env`, then restart **and re-index**. Existing
chunks retain the size they were split at, and there is no migration.

**Switch the vector backend.** `VECTOR_BACKEND=faiss`, install the extra (`pip install -e ".[faiss]"`),
restart — and expect an **empty** index (§3.1). Be aware that the FAISS delete path has a known defect
when removing the last indexed file; see [`ingestion/README.md`](ingestion/README.md) §8.

**Change the port.** `PORT` in `.env` — and update the proxy target in `Frontend/vue.config.js` to
match, or the dev server will proxy `/api` to a port nothing is listening on. Running both halves
through `python infra/dev.py` handles this for you by probing free ports and injecting them into the
child environment.

---

## 🔗 9. KNOWN DRIFT & DEEPER READING

**Convention exceptions, the exhaustive set.** The rule is *a setting is a `Config` attribute **and** an
`.env.example` line*. Four kinds of exception exist, and this is all of them:

| Kind | Members | Verdict |
|---|---|---|
| Env var with no `Config` attribute | `KB_REGISTRY_PATH` | A real exception; documented in the template, so at least discoverable |
| `Config` attribute with no `.env.example` line | `CHUNK_SIZE`, `CHUNK_OVERLAP` | A real gap — the one worth fixing first |
| Neither, **by design** | `VECTOR_ROOT`, `GRAPH_ROOT`, `KEYWORD_ROOT`, `MAX_CONTENT_LENGTH`, `ALLOWED_EXTENSIONS` | **Not violations** — there is no variable to document |
| Duplicated defaults across 16 call sites | §5 | A maintenance hazard; **currently all in agreement** |

**Stale comments in the source, verified this run.** These are code comments, not behaviour — the code
is right and the prose beside it is not:

- **`.gitignore:32-34`** describes the **retired** cwd-relative `DATA_ROOT` behaviour. Its two ignore
  entries are still correct; only the rationale is out of date.
- **`llm.py:20`** says the LLM cache key is a 3-tuple; the code uses a 4-tuple including `model`
  (`llm.py:39`).
- **`llm.py:30`** and **`reasoning.py:7`** cite a `JsonOutputParser` that does not exist anywhere in the
  repository — every JSON-consuming node uses `safe_json_parse`.
- **`query_routes.py:48`** says the `model` override is *"ignored for OpenAI"*; it is not
  (`llm.py:62`), and the frontend depends on it working.
- **`loader.py:115`** says chunk ids exist *"for Chroma upsert dedup"*; the call is `collection.add`,
  and dedup actually comes from the delete-before-write at `services.py:60`.
- **`hybrid_node.py:4`** says the three retrievers run *"in parallel"*; the code is three sequential
  synchronous calls.

**Where the defaults come from.** The values in `config.py` are not tuned against a benchmark — they are
conservative starting points for a single-machine tool: a small chunk so retrieval is precise, a
retrieval budget wide enough for the reranker to have something to choose from, a context cap low enough
that a small local model can hold it, and a retry budget of two because a third pass of a deterministic
pipeline cannot produce anything new. Each is explained where it bites, in the page that owns it.

**Continue reading:**

- [`ingestion/README.md`](ingestion/README.md) — `CHUNK_SIZE`, `ALLOWED_EXTENSIONS`, `UPLOAD_FOLDER` in use
- [`hybrid-retrieval/README.md`](hybrid-retrieval/README.md) — `RETRIEVAL_TOP_K`, `RERANK_TOP_K`, `RERANKER_MODEL`
- [`hybrid-retrieval/stores.md`](hybrid-retrieval/stores.md) — `VECTOR_BACKEND` and the four store paths
- [`llm-providers/README.md`](llm-providers/README.md) — every model, key and URL setting, and the credential path
- [`rag-pipeline/README.md`](rag-pipeline/README.md) — `MAX_CONTEXT_CHARS` and `MAX_REFLECTION_RETRIES`
- [`sse-event-bus/README.md`](sse-event-bus/README.md) — the hardcoded 180-second timeout
- [`security.md`](security.md) — the CORS, debug and authentication defaults, in full
