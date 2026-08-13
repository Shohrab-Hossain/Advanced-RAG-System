# Configuration

All configuration is environment variables. The backend reads `Backend/.env` via `python-dotenv` at import
time in `config.py`; the frontend reads `Frontend/.env` at build time via Vue CLI.

Both sides ship a committed `.env.example`. `.env` and `*.env` are gitignored, `.env.example` is
explicitly un-ignored.

> [!IMPORTANT]
> **Precedence: process environment → `Backend/.env` → the `config.py` default.** `config.py:13` calls
> `load_dotenv(…)` with a single positional argument and **no `override=`**, and `python-dotenv` defaults
> to `override=False` — so a variable already present in the process environment is **not** replaced by
> `.env`. That is the mechanism the root launcher relies on: `dev.py:229-235` injects `PORT` and
> `FRONTEND_URL` into the child process only and never writes a file, knowing a stale `.env` cannot
> override them. See [ADR-006](../../../decisions/ADRs/entries/006-dev-launcher-env-injected-ports.md).

<br>

## Backend variables

Defaults are from `Backend/src/config.py` (the authority) — where `.env.example` suggests a different
value, both are shown.

### LLM

| Variable | Default | Does |
|---|---|---|
| `OPENAI_API_KEY` | `""` | OpenAI credential. Empty ⇒ `/api/providers` reports OpenAI unavailable. **Never sent to the client.** |
| `LLM_MODEL` | `gpt-4o-mini` | OpenAI model name |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server root; probed at `{base}/api/tags` |
| `OLLAMA_MODEL` | `llama3.2` (`.env.example`: `llama3.2:latest`) | Default local model |
| `DEFAULT_PROVIDER` | `openai` | `openai` \| `ollama`; the fallback when a request omits `provider` |

### Models

| Variable | Default | Does |
|---|---|---|
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | SentenceTransformer used for chunk and query embeddings. **Changing it invalidates every existing vector** |
| `RERANKER_MODEL` | `cross-encoder/ms-marco-MiniLM-L-6-v2` | CrossEncoder used by the reranker |

Both download from Hugging Face on first use.

### Retrieval and generation knobs

| Variable | Default | Does |
|---|---|---|
| `RETRIEVAL_TOP_K` | `10` | Candidates per store (graph uses `max(k // 2, 3)`) |
| `RERANK_TOP_K` | `5` | Documents kept after reranking → the answer context |
| `MAX_CONTEXT_CHARS` | `4000` | Threshold above which the compressor runs; also the compression target |
| `MAX_REFLECTION_RETRIES` | `2` | Retry budget ⇒ at most 3 generation attempts |
| `CHUNK_SIZE` | `500` | Characters per chunk (not exposed in `.env.example`) |
| `CHUNK_OVERLAP` | `50` | Character overlap between chunks (not exposed in `.env.example`) |

> **Read-site warning.** `RETRIEVAL_TOP_K`, `RERANK_TOP_K`, `MAX_CONTEXT_CHARS`, `MAX_REFLECTION_RETRIES`,
> `CHUNK_SIZE`, and `CHUNK_OVERLAP` are read by the node/loader modules with `os.getenv` **at import
> time**, not through `Config`. Setting them in `.env` still works (dotenv loads before those imports),
> but changing them requires a restart, and mutating `Config` at runtime has no effect.

### Storage

| Variable | Default | Does |
|---|---|---|
| `DATA_ROOT` | `./data` | Base of everything on disk |
| `UPLOAD_FOLDER` | `<DATA_ROOT>/uploads` | Where uploaded files are saved; created at app start |
| `DATABASE_ROOT` | `<DATA_ROOT>/databases` | Base for all indexes |
| `CHROMA_PATH` | `<DATABASE_ROOT>/vector_db/chroma_db` | Chroma persistent directory |
| `FAISS_PATH` | `<DATABASE_ROOT>/vector_db/faiss_db` | FAISS pickle (index written to `<path>.idx`) |
| `GRAPH_PATH` | `<DATABASE_ROOT>/graph_db/graph_store/graph_store.pkl` | Entity-graph pickle |
| `BM25_PATH` | `<DATABASE_ROOT>/keyword_db/bm25_store/bm25_store.pkl` | BM25 corpus pickle |
| `KB_REGISTRY_PATH` | `<DATABASE_ROOT>/kb_registry.json` | KB registry (read only in `registry.py`, not in `Config`) |
| `VECTOR_BACKEND` | `chroma` | `chroma` \| `faiss`; lowercased. `faiss` requires `faiss-cpu` or the module raises at import |

Derived roots (not settable directly): `VECTOR_ROOT`, `GRAPH_ROOT`, `KEYWORD_ROOT` = `<DATABASE_ROOT>/`
plus `vector_db` / `graph_db` / `keyword_db`.

> **`.env.example` uses `${DATA_ROOT}` interpolation** in the storage paths. `python-dotenv` supports this
> in a `.env` file; `Config` composes the same paths in Python as a fallback when the variable is unset.

### Server

| Variable | Default | Does |
|---|---|---|
| `PORT` | **`5001`** (`config.py:68`; `.env.example:48` sets `5000`) | Flask listen port |
| `FLASK_DEBUG` | `true` | `Config.DEBUG`, compared case-insensitively to `"true"`. Werkzeug debugger **and** reloader on by default |
| `FRONTEND_URL` | `http://localhost:5173` | Added to the CORS origin allowlist. Injected by `dev.py:232` as the real UI URL when the launcher runs |

> **`PORT` is the one default where `config.py` and `.env.example` disagree**, and the disagreement is
> load-bearing: with no `.env` the API listens on **5001**, while the dev-server proxy's literal fallback
> targets `:5000` (`Frontend/vue.config.js:12`). Copy `.env.example` to `.env`, pass `PORT` explicitly, or
> run `python dev.py` (which pins both ports and wires the proxy to the one it chose).

Not environment-driven, but configuration all the same (`config.py`): `MAX_CONTENT_LENGTH = 50 MB`
(`config.py:61`) and `ALLOWED_EXTENSIONS` — **35 extensions**, not four (`config.py:62-65`):

```
pdf  txt  md   docx json csv  html htm
js   jsx  ts   tsx  css  scss py   java
c    cpp  cs   go   rb   php  rs   sh
bat  pl   swift kt  scala r    m    vb
lua  dart sql
```

The set is far wider than the four loader types suggest — it accepts source and script files
(`py`, `sh`, `bat`, `pl`, `js`) as indexable text. `Frontend/src/components/FileUpload.vue:77-84` carries
the same 35 entries as its `accept` list, so the two sides are in sync; keep them that way.

<br>

## Frontend variables

| Variable | Default | Does |
|---|---|---|
| `VUE_APP_API_URL` | `''` (falls back to relative URLs) | Base for every API call in `services/api.js:12`. Vue CLI only exposes variables prefixed `VUE_APP_`, and they are **baked into the bundle at build time**. Set by `dev.py:245` only under `--direct` |
| `DEV_API_TARGET` | unset → the literal `http://localhost:5000` | Where the dev-server proxy forwards `/api` (`vue.config.js:12`). Always exported by `dev.py:243` so the proxy follows the port the launcher chose |

**The two are deliberately different in kind.** `VUE_APP_API_URL` is compiled into the client bundle and
reaches the browser; `DEV_API_TARGET` is read by `vue.config.js` in the **Node dev-server process** and
never leaves the build host — which is exactly why it carries no `VUE_APP_` prefix. See
[`../../conventions/project-layout/README.md`](../../conventions/project-layout/README.md).

With `VUE_APP_API_URL` empty in development, requests go to relative `/api/*` paths and the dev server
proxy forwards them to `DEV_API_TARGET`, falling back to the `http://localhost:5000` literal.
`Frontend/.env.example:4` suggests setting `VUE_APP_API_URL=http://localhost:5001` — note that this is the
`config.py` default port, not the `.env.example` one.

<br>

## Storage layout on disk

`DATA_ROOT` defaults to the relative literal `"./data"` (`config.py:44`) and is resolved against the
**process working directory** — unlike `config.py:13`, which anchors the `.env` lookup to `__file__`. The
tree below therefore lands wherever the backend was started, and every path is created at **import time**
(`app.py:52`, `vector_store.py:18,49,51`, `bm25_store.py:17,32`).

```
<CWD>/data/                   (DATA_ROOT)
├── uploads/                  original uploaded files
└── databases/
    ├── kb_registry.json      the knowledge-base registry
    ├── vector_db/
    │   ├── chroma_db/        Chroma persistent files
    │   └── faiss_db          FAISS pickle (+ faiss_db.idx) — only if VECTOR_BACKEND=faiss
    ├── graph_db/
    │   └── graph_store/graph_store.pkl
    └── keyword_db/
        └── bm25_store/bm25_store.pkl
```

> [!CAUTION]
> **The live corpus is at `Backend/src/data/`, and it is not ignored.** The backend is started from
> `Backend/src`, so that is where the tree lands. `Backend/data/` **does not exist**, yet `.gitignore:29-30`
> ignore `Backend/data/databases/` and `Backend/data/uploads/` — two globs that match nothing. The
> consequence is live: `Backend/src/data/databases/vector_db/chroma_db/chroma.sqlite3` is **tracked in
> git** and grows with every ingest. Untrack it and fix the ignore paths before adding more data.
> Starting the backend from `Backend/` instead opens a second, empty corpus at `Backend/data/` — see
> [`../../runtime/backend-startup/README.md`](../../runtime/backend-startup/README.md).

Deleting `databases/` resets the index; deleting `uploads/` orphans the registry entries (their files can
then no longer be removed by `/api/clear`).

<br>

## Secrets

`OPENAI_API_KEY` is the only secret. It is read once in `config.py`, used only to construct `ChatOpenAI`
server-side, and exposed to clients solely as the boolean `available` on `/api/providers`. There is no
secret manager, no key rotation, and no encryption at rest — the key lives in `Backend/.env`, which is
gitignored.
