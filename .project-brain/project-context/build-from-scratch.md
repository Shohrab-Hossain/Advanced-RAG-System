# Build from scratch

The ordered reconstruction guide — from an empty machine to a running, verified adRAG. This is the **only**
place these steps live; the cookbooks point here.

Two modes are covered: **(A) rebuild from the existing repository** (install and run), and **(B) recreate
the project from nothing** using this brain as the specification.

<br>

---

<br>

## Prerequisites

| Need | Detail |
|---|---|
| Python | **3.10+** — required by `str \| None` unions and builtin generics used throughout `Backend/src/` |
| Node.js + npm | For the Vue CLI toolchain |
| An LLM provider | An `OPENAI_API_KEY`, **or** [Ollama](https://ollama.com) running locally with a model pulled (`ollama pull llama3.2`) |
| Disk + network | ~500 MB and internet access on first run — `all-MiniLM-L6-v2` and `cross-encoder/ms-marco-MiniLM-L-6-v2` download from Hugging Face |

No database server, message broker, or container runtime is needed.

<br>

---

<br>

## A. Rebuild from the repository

### 1. Backend

```bash
cd Backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `Backend/.env`: set `OPENAI_API_KEY`, or set `DEFAULT_PROVIDER=ollama` and confirm
`OLLAMA_BASE_URL` / `OLLAMA_MODEL`. Every variable and its default is specified in
[`operations/configuration/README.md`](operations/configuration/README.md).

### 2. Frontend

```bash
cd Frontend
npm install
cp .env.example .env               # VUE_APP_API_URL=http://localhost:5001
```

### 3. Start both halves

With the install steps above done, the root launcher is the one-command path:

```bash
python dev.py                      # from the repository root
```

It picks a free port for each half before spawning, starts both, waits for `/api/health`, prints the two
URLs it chose, and tears both down together. Flags: `--direct`, `--no-reload`, `--api-port`, `--ui-port`
(`dev.py:192-200`). Full behaviour and its verification status are in
[`operations/run-and-build/README.md`](operations/run-and-build/README.md); the startup traps it exists to
neutralise are in [`runtime/backend-startup/README.md`](runtime/backend-startup/README.md).

**Or start each half by hand:**

```bash
cd Backend/src && python main.py   # → http://localhost:5001 (no .env) or :5000 (with one)
cd Frontend    && npm run serve    # → http://localhost:8080
```

> [!WARNING]
> **The backend's working directory must be `Backend/src`.** `Config.DATA_ROOT` is the relative literal
> `"./data"` (`config.py:44`), resolved against the process CWD, and the live corpus is at
> `Backend/src/data/`. Starting from `Backend/` **imports fine** — `sys.path[0]` is the *script's*
> directory, not the CWD — and then silently creates and opens an empty `Backend/data/`. The working
> directory does not control the import root; it controls only which corpus you open. Corroboration: the
> documented gunicorn command uses `--chdir src` (`main.py:11`) and therefore lands in the right place,
> while the dev command documented beside it does not.

### 4. Verify

```bash
API=http://localhost:5001                    # or the URL dev.py / main.py printed

curl $API/api/health      # {"status":"healthy"}   ← one key, no version field
curl $API/api/providers   # at least one provider available:true
```

Then in the browser at the UI URL (`http://localhost:8080` by default):

1. `/knowledge-base` — drag in a PDF. The upload bar should run, then indexing, then the file appears with
   chunk / vector / entity counts.
2. `/chat` — ask a question about that document. All eight stages in the tracker should light up, and the
   answer should carry `[1]`-style citations with expandable source cards.
3. `/configuration` — confirm the provider you configured shows as available.

<br>

---

<br>

## B. Recreate the project from nothing

Build in this order — each step's specification is linked.

### 1. Scaffold

```
Advanced RAG System/
├── Backend/src/rag_pipeline/{core,encoding,generation,ingestion,ranking,retrieval}/
└── Frontend/src/{assets,components,router,services,stores,views}/
```

Add `__init__.py` to every Python package. Write the root `.gitignore` covering `__pycache__/`, venvs,
`.env`/`*.env` (un-ignoring `.env.example`), `node_modules/`, `Frontend/dist/`, and the runtime data tree.

> [!CAUTION]
> **Do not copy the shipped ignore paths — they are wrong.** `.gitignore:29-30` ignore
> `Backend/data/databases/` and `Backend/data/uploads/`, but `DATA_ROOT` is CWD-relative and the backend
> runs from `Backend/src`, so the real tree is `Backend/src/data/` and those globs match nothing. The
> live consequence: `Backend/src/data/databases/vector_db/chroma_db/chroma.sqlite3` is **tracked in git**.
> A rebuild should ignore **`Backend/src/data/`** (or set `DATA_ROOT` to an absolute path and ignore that).

Full layout and naming rules:
[`conventions/project-layout/README.md`](conventions/project-layout/README.md).

### 2. Backend configuration

Write `Backend/requirements.txt` and `Backend/src/config.py` per
[`overview/tech-stack.md`](overview/tech-stack.md) and
[`operations/configuration/README.md`](operations/configuration/README.md). `config.py` must
`load_dotenv(Path(__file__).parent.parent / ".env")` at import. Mirror every variable into
`Backend/.env.example` with its default.

### 3. The data layer

Implement, in this order — each depends on the previous:

1. `rag_pipeline/state.py` — `Document` and `RAGState`, per [`data/rag-state/README.md`](data/rag-state/README.md).
2. `rag_pipeline/core/events.py` — the session→queue bus, per
   [`runtime/sse-event-bus/README.md`](runtime/sse-event-bus/README.md).
3. `rag_pipeline/encoding/embeddings.py` and `llm.py` — the two singletons plus `safe_json_parse` and
   `check_ollama`, per [`features/llm-provider-selection/README.md`](features/llm-provider-selection/README.md).
4. `rag_pipeline/ingestion/loader.py` and `registry.py`, per
   [`runtime/ingestion-indexing/README.md`](runtime/ingestion-indexing/README.md) and
   [`data/kb-registry/README.md`](data/kb-registry/README.md).
5. The three stores under `rag_pipeline/retrieval/{vector,keyword,graph}/`, all sharing the same surface,
   per [`features/hybrid-retrieval/README.md`](features/hybrid-retrieval/README.md) and
   [`data/document-chunk/README.md`](data/document-chunk/README.md).

### 4. The pipeline

Write the eight nodes, then `graph.py`. Node behaviour, prompts, fallbacks, routing predicates, and the
retry/escalation heuristic are fully specified in
[`runtime/query-pipeline/README.md`](runtime/query-pipeline/README.md); the events each node must emit are
in [`api/sse-events/README.md`](api/sse-events/README.md).

Order: `planner` → `retrieval` → `web_node` → `aggregator` → `reranker` → `compressor` → `reasoning` →
`reflection` → `graph.py`.

### 5. The HTTP layer

`Backend/src/app.py` with `create_app()`, CORS, and the **eight** routes exactly as specified in
[`api/http/README.md`](api/http/README.md). Then `Backend/src/main.py` — logger suppression, warning
filters, and `app.run(debug, host="0.0.0.0", port, threaded=True)`.

For CORS, scope the resource to `r"/api/*"` and give `origins` a **genuinely explicit** list — the shipped
`app.py:44` ends its list with a literal `"*"`, which permits every origin against an API with no
authentication. Do not reproduce that entry; see
[`security/trust-boundaries/README.md`](security/trust-boundaries/README.md).

**Checkpoint:** from `Backend/src`, run `python main.py`, then `curl /api/health` (expect
`{"status":"healthy"}`), upload a file, and `curl /api/documents` to confirm non-zero counts. Do not move
on until the backend works standalone.

### 6. Frontend scaffold

`package.json` (deps per [`overview/tech-stack.md`](overview/tech-stack.md)), `vue.config.js`,
`tailwind.config.js` and `postcss.config.js`, and `public/index.html` with the title, meta description,
and the two Google Fonts links.

`vue.config.js` needs `devServer.port = 8080` and an `/api` proxy whose target is **env-driven with a
literal fallback**:

```js
target: process.env.DEV_API_TARGET || 'http://localhost:5000'   // vue.config.js:12
```

The fallback keeps a bare `npm run serve` working; the environment variable is what lets `dev.py` point
the proxy at whichever API port it picked. Build it the other way round — a hardcoded target — and the
launcher cannot wire a floating port. `DEV_API_TARGET` deliberately carries **no** `VUE_APP_` prefix: it is
read in the Node dev-server process and must not be inlined into the client bundle.

### 7. Design layer

`src/assets/main.css` — the Tailwind entry plus the `@layer base/components/utilities` blocks. Every token,
class, and animation is specified with real values in [`design/theme/README.md`](design/theme/README.md).

### 8. State and services

`src/services/api.js` (seven call wrappers — `uploadFile`, `getDocuments`, `clearDocuments`,
`healthCheck`, `getProviders`, `getKnowledgeBases`, `deleteKnowledgeBase` — plus `streamQuery`'s
fetch+reader loop, eight exports in all) and `src/stores/`
(`rag.js` with `STAGES` and `_applyEvent`, `ui.js` with the theme and modal). Specified in
[`architecture/frontend.md`](architecture/frontend.md), with the event mapping in
[`features/pipeline-tracker/README.md`](features/pipeline-tracker/README.md) and the history contract in
[`features/chat-history/README.md`](features/chat-history/README.md).

### 9. Components and views

`main.js` → `App.vue` → `router/index.js` → the four views → the twelve components. Per-component
responsibilities, props, and emits are tabulated in [`architecture/frontend.md`](architecture/frontend.md).

### 10. Verify end to end

Run the checks in section A.4 above. The rebuild is complete when a query against an uploaded document
produces a cited answer and all eight tracker stages report.

Optionally add the root `dev.py` launcher last — it is not required by the application, only by the
developer workflow. Its contract and rejected alternatives are recorded in
[ADR-006](../decisions/ADRs/entries/006-dev-launcher-env-injected-ports.md).

<br>

---

<br>

## Notes and gotchas for a rebuild

- **`stage` ids are a contract.** The backend's node names and the frontend's `STAGES` ids must match
  exactly, or the tracker silently ignores events.
- **Start the backend from `Backend/src`.** Not from `Backend/`, and not from the repo root. The reason is
  **`DATA_ROOT`, not imports**: `config.py:44` resolves `"./data"` against the process CWD, so the wrong
  directory opens an empty corpus instead of the live one. Imports are unaffected either way, because
  `sys.path[0]` is the script's directory — which is exactly why the mistake is silent.
- **Single worker only** if you use gunicorn (`-w 1 --chdir src`); the SSE queues and store singletons are
  per-process. `--chdir src` also happens to supply the correct `DATA_ROOT`, so the production command
  lands in the right directory. `gunicorn` is not in `requirements.txt`.
- **`PORT` falls back to 5001, not 5000** (`config.py:68`), while `.env.example:48` sets 5000 and the
  dev-server proxy's literal fallback targets 5000. Without a `.env`, the frontend cannot reach the API.
- **`GET /api/health` returns `{"status":"healthy"}`** and nothing else (`app.py:309`). There is no
  `version` field — do not treat its absence as a failed build.
- **`VUE_APP_API_URL` is baked in at build time**, so a production bundle needs the API origin known before
  `npm run build`.
- **Changing `EMBEDDING_MODEL` or the chunk parameters invalidates the index** with no error — clear and
  re-upload.
- **First request is slow** while the two Hugging Face models download.

There are **no tests to run** — the repository has no test suite. Verification is the manual checklist
above.
