# Run and build

Two halves that can each run alone, plus a root launcher that runs both together. Commands are as
implemented in `dev.py`, `Backend/src/main.py`, `Backend/src/config.py`, `Frontend/package.json` and
`Frontend/vue.config.js`.

<br>

## Prerequisites

| Need | Why |
|---|---|
| Python **3.10+** | The code uses `str \| None` and builtin generics. No version is declared in the repo — this is the floor the syntax requires |
| Node.js + npm | For the Vue CLI toolchain (no engines field is declared). `dev.py:103-108` resolves `npm` via `shutil.which` and exits if it is missing |
| An `OPENAI_API_KEY` **or** a running Ollama | At least one LLM provider must be reachable |
| ~500 MB free disk + network on first run | The embedding and reranker models download from Hugging Face |

<br>

---

<br>

## Step 1 — install (required before anything else)

There is currently **no virtualenv in the repository**, and the launcher looks for one first
(`dev.py:92-100`: `Backend/.venv` → `Backend/venv` → `Backend/env`, else `sys.executable` with a warning).
Without this step the backend child dies at `ModuleNotFoundError`.

```bash
cd Backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # then set OPENAI_API_KEY (or configure Ollama)
cd ../Frontend
npm install
```

<br>

---

<br>

## Step 2 — run both halves: `python dev.py`

**This is the development entry point.** From the repository root:

```bash
python dev.py
```

It picks a free port for each half **before** spawning anything, starts both, prefixes and interleaves
their logs, waits for the API to answer `/api/health`, prints the two URLs it actually chose
(`dev.py:248-249`), and tears both halves down together when either one dies or you press Ctrl-C.

| Flag | Effect | Where |
|---|---|---|
| *(none)* | Frontend calls relative `/api/*`; the dev-server proxy forwards to the chosen API port via `DEV_API_TARGET` | `dev.py:243`, `Frontend/vue.config.js:12` |
| `--direct` | Also exports `VUE_APP_API_URL`, so the browser calls the API origin directly instead of through the proxy | `dev.py:243-245` |
| `--no-reload` | Sets `FLASK_DEBUG=false` in the child environment — no Werkzeug reloader, no debugger | `dev.py:236-237` |
| `--api-port <n>` | Pins the API port instead of probing | `dev.py:192-200` |
| `--ui-port <n>` | Pins the dev-server port instead of probing | `dev.py:192-200` |

**Why it exists rather than two terminals** — it removes four silent-failure modes at once: the wrong
working directory, the `PORT` default, a stale `.env`, and a reloader child that keeps the port after its
parent is killed. Each is documented in
[`../../runtime/backend-startup/README.md`](../../runtime/backend-startup/README.md), with the design
rationale in [ADR-006](../../../decisions/ADRs/entries/006-dev-launcher-env-injected-ports.md).

> [!IMPORTANT]
> **What is and is not verified.**
> **Verified end to end:** a real backend boot · the `/api/health` readiness poll (`backend healthy after
> 12s`) · live REST routes through the proxy (`/api/health`, `/api/providers`, `/api/documents`) · port
> probing, including prefer-then-walk under real contention — `5000` and `8080` were both taken, so the
> run landed on `5001`/`8081` and the frontend followed automatically · dual spawn · prefixed log
> muxing · child-death detection · Windows process-tree teardown, confirmed by both ports being released
> afterwards.
> **Not verified:** SSE through the launcher (`POST /api/query`) needs a configured provider, and no
> `Backend/.env` exists yet — see Step 2 · the reloader's double-load, because the verifying run used
> `--no-reload`.

<br>

---

<br>

## Fallback — start each half by hand

Use this when you need one half only, or when the launcher is unavailable.

### Backend

```bash
cd Backend/src
python main.py                     # → http://localhost:5001 with no .env, :5000 with one
```

> [!WARNING]
> **Start from `Backend/src`, not from `Backend/`.** `Config.DATA_ROOT` defaults to the relative literal
> `"./data"` (`config.py:44`) and is resolved against the process working directory, while the live corpus
> lives at `Backend/src/data/`. Starting from `Backend/` still imports fine — `sys.path[0]` is the
> *script's* directory, not the CWD — and then silently creates and opens an **empty** `Backend/data/`.
> The import root is not what the working directory controls; the corpus is.

`main.py` prints the API URL and the three active model names on start, then runs Flask with
`debug=Config.DEBUG`, `host="0.0.0.0"`, `port=Config.PORT`, `threaded=True` (`main.py:35-39`).
`Config.PORT` falls back to **5001** (`config.py:68`) while `Backend/.env.example:48` sets `PORT=5000`, so
the port depends on whether you copied the `.env`.

**Production-ish alternative** (from `main.py:10-11`):

```bash
cd Backend
gunicorn -w 1 -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker \
         --bind 0.0.0.0:5000 --chdir src main:app
```

Two constraints are load-bearing here. **`--chdir src`** does two jobs: gunicorn imports `main:app` as a
module with the CWD on `sys.path`, *and* the same `--chdir` silently supplies the correct `DATA_ROOT` — so
the production command lands in the right directory while the hand-written dev command above only does if
you follow the warning. **`-w 1`**, because the SSE session queues and the three store singletons are
per-process memory. Note that `gunicorn` and the gevent worker package are **not** in `requirements.txt` —
install them separately if you use this path.

### Frontend

```bash
cd Frontend
npm run serve     # dev server → http://localhost:8080
npm run build     # production bundle → Frontend/dist/
npm run lint      # vue-cli-service lint — see below
```

The dev server proxies `/api` to `process.env.DEV_API_TARGET || 'http://localhost:5000'`
(`vue.config.js:12`), so no CORS setup is needed during development. Under `dev.py` that variable carries
the port the launcher chose; run bare, it falls back to the `:5000` literal — which will **not** reach a
backend started without a `.env` (that one is on 5001).

> [!WARNING]
> **`npm run lint` does not work today.** The script is `vue-cli-service lint`, but
> `@vue/cli-plugin-eslint` is absent from `Frontend/package.json` `devDependencies`, from
> `Frontend/node_modules/@vue/`, and from `package-lock.json`, and no ESLint config file exists. Install
> the plugin and add a config before relying on it.

`dist/` is gitignored and there is no configured way to serve it — a production deployment would need a
static host plus a reachable API origin baked into `VUE_APP_API_URL` **at build time**.

<br>

---

<br>

## First-run behaviour

1. `Config` loads `Backend/.env` (`config.py:13`, path anchored to `__file__` so it is found from any
   directory); `create_app()` creates `UPLOAD_FOLDER` (`app.py:52`, called at module scope by
   `app.py:316`).
2. The three store singletons initialise at import: Chroma creates `CHROMA_PATH` and the `rag_documents`
   collection; the BM25 and graph stores create their parent directories and load their pickles if present.
   **These paths are resolved from the working directory** — see the backend warning above.
3. **Models download lazily, not at boot** — the embedder loads on the first upload or query, the
   cross-encoder on the first rerank. Expect a long first request.
4. `NavBar.vue` calls `/api/health` on mount to light the connectivity dot, then fetches stats, providers,
   and the KB list.
5. With an empty index, a query still runs: retrieval returns nothing, the reasoning node falls through to
   its no-context branch, and the answer ships with zero sources.

> [!NOTE]
> `FLASK_DEBUG` defaults to `true` (`config.py:67`), so the Werkzeug reloader is on unless you pass
> `--no-reload` or set it yourself. `dev.py`'s own comments state that this makes the models load twice and
> roughly doubles boot time (`dev.py:10`, `dev.py:196-197`) — code-asserted, not independently observed.

<br>

---

<br>

## Verify it works

Under `dev.py`, use the two URLs the launcher printed. Standalone, substitute the port the backend
reported on start (5001 with no `.env`, 5000 with one) — the examples below use `$API` for that reason.

```bash
API=http://localhost:5001                  # or whatever dev.py / main.py printed

curl $API/api/health          # → {"status":"healthy"}
curl $API/api/providers       # → availability of openai / ollama
curl -F "file=@some.pdf" $API/api/upload
curl $API/api/documents       # → non-zero vector_count / bm25_count
```

`GET /api/health` returns **exactly** `{"status": "healthy"}` (`app.py:309`) — one key, no `version`
field. Do not treat a missing version string as a failed build.

Then open the UI (`http://localhost:8080` by default), upload a document on `/knowledge-base`, and ask a
question on `/chat` — the pipeline tracker should light all eight stages.

<br>

---

<br>

## Tests, CI, deployment

None exist. There is no test suite, no CI workflow, no Dockerfile, and no infrastructure code in the
repository — `dev.py` is a development launcher, not a deployment path. TODO: confirm with the owner
whether any of these are planned before treating their absence as intentional.
