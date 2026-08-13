# Runtime: backend startup

What happens between issuing a start command and a serving Flask process — and the four traps that let the
backend come up **looking** healthy while being wrong. Implemented in `Backend/src/main.py`,
`Backend/src/config.py`, `Backend/src/app.py` and the three store modules; automated by the root launcher
`dev.py`.

The static structure is in [`../../architecture/backend.md`](../../architecture/backend.md); the commands
themselves are in [`../../operations/run-and-build/README.md`](../../operations/run-and-build/README.md).

<br>

---

<br>

## The startup sequence

Everything below happens at **import time**, before Flask binds a socket:

| # | Step | Where | Depends on |
|---|---|---|---|
| 1 | `.env` is loaded | `config.py:13` — `load_dotenv(Path(__file__).parent.parent / ".env")` | **`__file__`**, so the file is found from any CWD |
| 2 | `Config` reads every variable once | `config.py` class body | the process environment, then `.env` |
| 3 | `create_app()` runs at module scope and `makedirs` the upload folder | `app.py:316`, `app.py:52` | `Config.UPLOAD_FOLDER` → `DATA_ROOT` |
| 4 | The three stores resolve their paths and create their directories | `vector_store.py:18,49,51` · `bm25_store.py:17,32` · `registry.py:15` | `Config.DATABASE_ROOT` → `DATA_ROOT` |
| 5 | Flask binds and serves | `main.py:35-39` — `app.run(debug=Config.DEBUG, host="0.0.0.0", port=Config.PORT, threaded=True)` | `Config.PORT`, `Config.DEBUG` |

Steps 3 and 4 are the reason the traps below are silent: **the corpus is chosen before a single request
arrives**, and choosing the wrong one is indistinguishable from an empty one.

<br>

---

<br>

## Trap 1 — the working directory picks the corpus

`Config.DATA_ROOT` is a **relative literal**, resolved against the process CWD:

```python
DATA_ROOT: str = os.getenv("DATA_ROOT", "./data")     # config.py:44
```

Contrast `config.py:13`, which anchors the `.env` lookup to `__file__`. `DATA_ROOT` is not anchored to
anything, so every store path underneath it moves with the directory the process was started in.

**The live corpus sits at `Backend/src/data/`.** `Backend/data/` does not exist. Therefore:

| Started from | Imports | Corpus opened |
|---|---|---|
| `Backend/src/` | ✅ | `Backend/src/data/…` — **the live one** |
| `Backend/` | ✅ | `Backend/data/…` — **created empty, on the spot** |

There is no error, no warning, and no log line. The API answers, `/api/documents` reports zeroes, and every
query returns an ungrounded answer.

> [!IMPORTANT]
> **The correct CWD is `Backend/src`.** Start the backend as `cd Backend/src && python main.py`, or let
> `dev.py` do it (`dev.py:256` spawns with `cwd=Backend/src`).

<br>

### The reason is `DATA_ROOT` — it is **not** the import root

A widespread and wrong justification for `cd Backend` is "so `src/` resolves as the import root". It does
not work that way. For `python <path>/script.py`, **`sys.path[0]` is the *script's* directory**, not the
CWD. Verified empirically with a subprocess probe run from both directories:

| Invocation | CWD | `sys.path[0]` |
|---|---|---|
| `python src/main.py` from `Backend/` | `…\Backend` | `…\Backend\src` |
| `python main.py` from `Backend/src/` | `…\Backend\src` | `…\Backend\src` |

Identical. `from config import Config` and `from rag_pipeline… import …` resolve from **either** directory.
The CWD controls **only** `DATA_ROOT` — which is precisely why the failure is silent: the half that would
have raised (imports) is unaffected, and the half that stays quiet (data) is the one that breaks.

`registry.py:18` carries a second CWD-relative literal — a legacy-migration check against
`./data/kb_registry.json` — so the same trap has a second entrance.

<br>

### Dev and production currently disagree

The documented gunicorn command uses `--chdir src` (`main.py:11`), which lands the CWD in `Backend/src` and
gets the **right** data directory. The dev command documented alongside it (`main.py:4-6`,
`cd Backend && python src/main.py`) does not. Production is correct today; the documented dev path is not.

<br>

---

<br>

## Trap 2 — `PORT` falls back to 5001, not 5000

```python
PORT: int = int(os.getenv("PORT", "5001"))            # config.py:68
```

`Backend/.env.example:48` sets `PORT=5000`. So the port depends on whether a `.env` exists:

| Condition | Listen port |
|---|---|
| No `Backend/.env` | **5001** |
| `.env` copied from `.env.example` | 5000 |
| `PORT` in the process environment | that value — it wins (see Trap 3) |

The Vue dev-server proxy's literal fallback targets `http://localhost:5000` (`Frontend/vue.config.js:12`),
so a backend started **without** a `.env` is on 5001 and a bare `npm run serve` cannot reach it. The
symptom is a frontend that loads fine and fails every API call.

<br>

---

<br>

## Trap 3 — process environment beats `.env`

`config.py:13` calls `load_dotenv(…)` with a single positional argument and **no `override=`**.
`python-dotenv`'s default is `override=False`, so **a variable already present in the process environment
is not replaced by `.env`.**

This is not a bug — it is the mechanism the launcher's whole design rests on. `dev.py` injects `PORT`,
`FRONTEND_URL`, `PYTHONUNBUFFERED` and `PYTHONIOENCODING` into the **child's** environment only
(`dev.py:229-235`) and writes nothing to disk, confident that a stale `.env` cannot override them. See
[ADR-006](../../../decisions/ADRs/entries/006-dev-launcher-env-injected-ports.md).

Precedence, highest first: **process env → `Backend/.env` → the `config.py` default.**

<br>

---

<br>

## Trap 4 — the debug reloader

`FLASK_DEBUG` defaults to `"true"` (`config.py:67`), so `Config.DEBUG` is `True` and `app.run(debug=True)`
(`main.py:35-39`) starts Werkzeug with **both** the interactive debugger and the auto-reloader.

> [!NOTE]
> **The two consequences below are code-asserted, not observed.** They are stated in `dev.py`'s own
> comments and help text (`dev.py:10`, `dev.py:146-148`, `dev.py:196-197`) and have **not** been
> independently reproduced: the boot that verified the launcher ran with `--no-reload`, which is exactly
> the flag that bypasses this path. Treat them as the launcher's stated rationale.

- **The models load twice and boot takes roughly twice as long.** The reloader re-executes the module in a
  child process, so every import-time cost is paid again (`dev.py:10`, `dev.py:196-197`).
- **The forked child is what holds the listening port.** Killing the parent PID alone leaves the port
  occupied, which is why teardown must kill the whole process tree (`dev.py:146-148`).

`dev.py --no-reload` sets `FLASK_DEBUG=false` in the child environment (`dev.py:236-237`) to avoid both.

The debugger half is a separate, security-relevant default — see
[`../../security/trust-boundaries/README.md`](../../security/trust-boundaries/README.md).

<br>

---

<br>

## What `dev.py` does about each

The root launcher exists to make the four traps unreachable by default.

| Trap | The launcher's answer | Where |
|---|---|---|
| Wrong CWD | Spawns the backend with `cwd=Backend/src`, argv `['<python>', 'main.py']` | `dev.py:256`, `dev.py:32` |
| Port fallback / collisions | Probes **both** ports with `socket.bind` **before** spawning; prefer-then-walk from `5000` / `8080` across a 40-port span; no `SO_REUSEADDR`, because a `TIME_WAIT` port is not free enough to hand out | `dev.py:70-89`, `dev.py:36-40`, `dev.py:74`, `dev.py:221-222` |
| Stale `.env` | Injects `PORT` and `FRONTEND_URL` into the child environment only — nothing written to disk | `dev.py:229-235` |
| Reloader child holds the port | Windows `taskkill /F /T /PID`; POSIX `killpg` SIGTERM then SIGKILL after 5 s | `dev.py:144-168`, `dev.py:154-159` |
| Reloader double-load | `--no-reload` sets `FLASK_DEBUG=false` | `dev.py:236-237` |

Alongside that it resolves the interpreter (`Backend/.venv` → `venv` → `env`, else `sys.executable` with a
warning — `dev.py:92-100`), resolves `npm` via `shutil.which` and exits if it is missing
(`dev.py:103-108`), pins the frontend port with `npm run serve -- --port <n>` (`dev.py:259`), muxes both
children's output behind per-half prefixes (`dev.py:133-141`), polls `GET /api/health` for readiness on a
240 s budget at 1 s intervals (`dev.py:44-45`, `dev.py:173-187`), watches for either child dying every
0.3 s and tears both halves down together (`dev.py:266-271`), and prints the two URLs it actually chose
(`dev.py:248-249`).

Frontend wiring: `DEV_API_TARGET` is **always** exported so the dev-server proxy follows the chosen API
port; `VUE_APP_API_URL` is exported **only** under `--direct` (`dev.py:243-245`). See
[`../../architecture/frontend.md`](../../architecture/frontend.md) for the two seams that creates.

<br>

---

<br>

## Verification status

State this plainly rather than assuming the launcher is proven end to end.

| | Paths |
|---|---|
| **Verified** | A real backend boot · the `/api/health` readiness poll against a live server (`backend healthy after 12s`) · live REST routes through the proxy (`/api/health`, `/api/providers`, `/api/documents`) · port probing including prefer-then-walk under real contention (`5000`/`8080` both held → `5001`/`8081`, frontend followed automatically) · interpreter and `npm` resolution · dual spawn · prefixed log muxing · child-death detection · Windows process-tree teardown, confirmed by both ports being released after stop · `DEV_API_TARGET` → proxy wiring |
| **Not verified** | SSE through the launcher (`POST /api/query`) — needs a configured provider, and no `Backend/.env` exists · the reloader's double-load and port-holding behaviour (code-asserted only, see Trap 4; the verifying run used `--no-reload`) |

> [!NOTE]
> **The venv prerequisite is closed.** `Backend/.venv` now exists with `requirements.txt` installed, and
> `python dev.py --no-reload` boots the backend end to end. A venv is **platform-specific**, though: this
> one is a Windows build (`Scripts/python.exe`, no `bin/`), so it cannot be used from WSL. Running
> `python3 dev.py` under WSL against it fails — `dev.py:105-112` now detects that case and reports the
> platform mismatch rather than falling back silently, and `_check_backend_deps` (`dev.py:118-133`) fails
> fast with the install command when the resolved interpreter has no Flask.
