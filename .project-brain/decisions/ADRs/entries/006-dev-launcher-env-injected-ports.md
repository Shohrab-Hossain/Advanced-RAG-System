# ADR-006: One dev launcher owns both ports, injected as child-process env
Date: 2026-08-13 · Status: accepted

> **Recorded at decision time** — this decision was made and written down in the same session, unlike
> ADRs 001–005, which were reconstructed from the code. The *Context*, *Decision*, and *Alternatives* below
> are the reasoning as it was actually weighed; every mechanism claim is additionally grounded in
> `dev.py`, `Frontend/vue.config.js`, `Frontend/src/services/api.js`, and `Backend/src/config.py`.
> The **Verification status** section states plainly which paths have been exercised and which have not.

## Context

The system ships as **two independently runnable halves** that share nothing but the HTTP contract — there
is no root `package.json`, no workspace tool, no Makefile. They are also deployed to two different places:
the Vue SPA to **AWS Amplify**, the Flask API to **EC2/GCP**. That split produces two distinct client→API
seams, and the development story has to serve both without collapsing them:

| Seam | How the frontend reaches the API | What governs it |
|---|---|---|
| **Proxied** (normal dev) | `VUE_APP_API_URL` unset → `BASE = ''` (`Frontend/src/services/api.js:12`) → relative URLs → dev-server proxy (`Frontend/vue.config.js:12`) | Same-origin; CORS never engages |
| **Direct** (deployed shape) | `VUE_APP_API_URL` set at build time → absolute URLs → cross-origin | The origins allowlist at `Backend/src/app.py:44` |

Development needs both halves up at once with HMR intact, and the backend port has to be able to **float**
when something else already holds the preferred one — with the frontend following it **without a manual
edit**. Three properties of the existing code shape what is and is not possible:

- **`load_dotenv()` is called with a single positional argument** (`Backend/src/config.py:13`), so
  python-dotenv's default `override=False` applies: a variable already present in the process environment
  **wins over `Backend/.env`**. A parent process can therefore configure the child without touching a file.
- **`PORT` falls back to `5001`** (`Backend/src/config.py:68`) while `Backend/.env.example:48` sets `5000`
  — so the port a fresh clone actually binds depends on whether a `.env` was copied.
- **`DATA_ROOT` is `./data`, resolved against the process CWD** (`Backend/src/config.py:44`), and every
  store creates its directory at import time. `Backend/data/` does not exist; the live corpus is at
  `Backend/src/data/`. The CWD a launcher chooses therefore decides which knowledge base opens.

One more constraint rules out the obvious implementation: **the port cannot be scraped from the backend's
own output.** The banner is printed before `app.run()` (`Backend/src/main.py:31`), the Werkzeug reloader is
on by default (`FLASK_DEBUG` defaults `true`, `Backend/src/config.py:67`) and re-executes the process, so
the banner appears **twice** and a parse of it is ambiguous as well as racy.

## Decision

Add a **`dev.py` launcher at the repo root** that owns both child processes and both ports. Seven points,
each deliberated rather than defaulted:

**1. The launcher picks both ports *before* either process starts.** `_port_is_free()` / `_find_free_port()`
bind-probe candidates (`dev.py:70-89`) and both ports are resolved up front (`dev.py:221-222`). Because
selection precedes spawn, the frontend can be configured **deterministically with no race** — there is
nothing to wait for and nothing to parse. `SO_REUSEADDR` is deliberately *not* set on the probe socket
(`dev.py:74`): a port in `TIME_WAIT` is not free enough to hand to a server.

**2. Prefer-then-walk, not an ephemeral port.** Try `5000`, then `5001`, and onward across a 40-port span;
the UI walks the same way from `8080` (`dev.py:36-40`). On a normal day the ports are the *stable, expected*
ones, so `curl`, Postman and browser bookmarks keep working; they float **only on an actual collision**. A
random/ephemeral port would break every external tool on every run for no gain.

**3. Configuration is injected as child-process environment only — no file is written.** `PORT`,
`FRONTEND_URL`, `PYTHONUNBUFFERED` and `PYTHONIOENCODING` go into the backend child's env (`dev.py:229-235`);
`DEV_API_TARGET` (always) and `VUE_APP_API_URL` (only under `--direct`) go into the frontend child's
(`dev.py:243-245`). Nothing lands in the repo, so **there is no generated artifact to gitignore and none to
drift**. This rests on the real `override=False` property above: a launcher-set `PORT` already beats
`Backend/.env`, so no file needs rewriting to win.

**4. The frontend seam stays additive.** `Frontend/vue.config.js:12` reads
`process.env.DEV_API_TARGET || 'http://localhost:5000'`. The literal fallback is deliberate: a bare
`npm run serve` must keep working standalone. The launcher is a **convenience layered over the existing
setup, never a new dependency of it**.

**5. Dev and prod seams stay distinct.** `Frontend/src/services/api.js:12` already reads
`process.env.VUE_APP_API_URL || ''`, so relative URLs ride the dev proxy while production supplies an
absolute URL. The launcher **preserves that split rather than collapsing it**, and a `--direct` flag
(`dev.py:192-200`, `dev.py:243-245`) opts into the absolute-URL path on demand — a way to rehearse the
cross-origin behaviour the Amplify→EC2 topology will have, on the machine, before deploying.

**6. Both ports are pinned, not just the backend's.** The UI port is passed through as
`npm run serve -- --port <n>` (`dev.py:259`), because Vue CLI otherwise silently auto-increments off `8080`
— and then the URL the launcher printed (`dev.py:248-249`) would be wrong.

**7. Teardown kills the process *tree*, per platform.** On Windows, `taskkill /F /T /PID`
(`dev.py:154-159`); on POSIX, a new session plus `killpg` with `SIGTERM` escalating to `SIGKILL` after 5s
(`dev.py:144-168`). The reason is the reloader: it forks a child that holds the port, so killing only the
spawned PID leaves the real server alive and the port occupied.

Supporting mechanics: the interpreter is resolved from `Backend/.venv` → `venv` → `env`, else `sys.executable`
with a warning (`dev.py:92-100`); `npm` is resolved via `shutil.which` and its absence is a clean exit
(`dev.py:103-108`); the backend is spawned with **`cwd=Backend/src`** (`dev.py:32`, `dev.py:256`) — the
comment at `dev.py:30-31` records why; readiness is polled at `GET /api/health` on a 240s budget at 1s
intervals (`dev.py:44-45`, `dev.py:173-187`); a child death is detected on a 0.3s loop and tears both halves
down (`dev.py:266-271`); `--no-reload` sets `FLASK_DEBUG=false` (`dev.py:236-237`).

## Alternatives considered

- **Let Flask bind first and scrape the port from its stdout** — *rejected.* It is racy (the frontend can
  only be configured after the backend is already up), and the reloader prints its banner **twice**
  (`Backend/src/main.py:31` + `FLASK_DEBUG` default `true` at `Backend/src/config.py:67`), so the parse is
  ambiguous on top of being late. Choosing the port first removes both problems at once.
- **Bind an ephemeral / random port (`:0`) and report it** — *rejected.* It always succeeds, but it breaks
  every external tool — saved `curl` invocations, Postman collections, browser bookmarks — on **every**
  run, in exchange for avoiding a collision that is rare. Prefer-then-walk pays that cost only when a
  collision actually happens.
- **Write the chosen values into a `.env` (or a generated config file) in the repo** — *rejected.* It would
  mutate a user-owned file, create an artifact to gitignore, and leave a stale value behind after a crash.
  `override=False` (`Backend/src/config.py:13`) makes env injection strictly sufficient, so the file buys
  nothing.
- **Make the launcher the mandatory entry point** (drop the literal fallback, require `DEV_API_TARGET`) —
  *rejected.* `Frontend/vue.config.js:11-12` keeps the `http://localhost:5000` literal precisely so a bare
  `npm run serve` still works standalone. The launcher must remain removable.
- **Pin only the backend port and let Vue CLI pick its own** — *rejected* for the reason in Decision 6: the
  auto-increment is silent, and the launcher would then print a URL that is not the one serving.

## Consequences

**Makes easy**

- **One command runs the whole system**, with both ports chosen, both logs prefixed and muxed, and both
  children torn down together.
- **A port collision is a non-event.** Nothing needs editing in `Backend/.env` or `Frontend/vue.config.js`;
  the proxy target follows automatically.
- **No repo mutation, so nothing to clean up.** No generated file, no gitignore entry, no stale value
  surviving a crash.
- **The correct corpus opens.** Spawning with `cwd=Backend/src` (`dev.py:256`) sidesteps the CWD trap that
  the manual `cd Backend && python src/main.py` walks straight into.
- **The deployed cross-origin shape is rehearsable locally** via `--direct`, without a build pipeline.

**Makes hard / watch out for**

- **The backend MUST run with CWD `Backend/src`, not `Backend/`.** `DATA_ROOT` is CWD-relative
  (`Backend/src/config.py:44`) and the live stores are at `Backend/src/data/`. Starting from `Backend/`
  imports fine — `sys.path[0]` is the *script's* directory, not the CWD — and silently opens an **empty**
  knowledge base. Any change to how the child is spawned must preserve that CWD.
- **A venv is a hard prerequisite.** `dev.py:92-115` looks for `Backend/.venv` first, and because a venv is
  platform-specific it distinguishes two failures: one built for the *other* platform (a Windows
  `Scripts/python.exe` seen from WSL, or the reverse) raises with that diagnosis at `dev.py:105-112`, while
  no venv at all falls back to `sys.executable` with a warning. `_check_backend_deps` (`dev.py:118-133`)
  then probes for Flask and exits with the exact install command. Both exist because the original silent
  fallback made a missing venv look like a launcher bug: the backend child died at `ModuleNotFoundError`
  many lines deep in the muxed log.
- **`--no-reload` exists because the reloader loads `sentence-transformers` and Chroma twice**, roughly
  doubling boot time (`dev.py:10`, `dev.py:196-197`). Turning the reloader off costs hot-reload of backend
  code.
- **The tree-kill is load-bearing and platform-specific.** Any refactor that terminates only the spawned PID
  will leave an orphaned reloader child holding the port, and the next run will walk to the next port
  instead — a silent, confusing symptom.
- **`--direct` moves the run onto the origins allowlist at `Backend/src/app.py:44`.** That list currently
  contains a literal `"*"` alongside the named origins, against an API with **no authentication on any
  route** — so `--direct` works today, and will keep working after deploy *from every origin on the
  internet*. That is an over-permission trap, not a CORS failure; see
  [`../../../project-context/security/trust-boundaries/README.md`](../../../project-context/security/trust-boundaries/README.md).
- **The launcher does not change the underlying defaults.** A backend started *without* the launcher and
  *without* a `.env` still binds `5001` (`Backend/src/config.py:68`) while the `vue.config.js` fallback
  targets `5000` — the mismatch the launcher hides, not one it fixes.
- **`dev.py` is untracked** at the time of writing (`git status` → `?? dev.py`), so it does not yet travel
  with a clone.

**Verification status at the time of this record**

Stated exactly, because a promoted entry point that has not completed a real boot is easy to over-trust.

| Path | Status |
|---|---|
| Port probing / prefer-then-walk (`dev.py:70-89`) | **Verified** |
| Interpreter + `npm` resolution (`dev.py:92-108`) | **Verified** |
| Dual spawn (`dev.py:256`, `dev.py:259`) | **Verified** |
| Prefixed log muxing (`dev.py:133-141`) | **Verified** |
| Child-death detection (`dev.py:266-271`) | **Verified** |
| Windows process-tree teardown (`dev.py:154-159`) | **Verified** |
| `DEV_API_TARGET` → proxy wiring (`dev.py:243` + `Frontend/vue.config.js:12`) | **Verified** — a stub backend on port `5017` was reached through the dev proxy at `/api/health`, returning the stub's payload |
| A real backend boot | **Verified** — `Backend/.venv` built and `requirements.txt` installed; `python dev.py --no-reload` brought the Flask app up and it served requests |
| The `/api/health` readiness poll against a live server (`dev.py:173-187`) | **Verified** — reported `backend healthy after 12s`, matching the server's own `200` for `GET /api/health` |
| Live REST routes through the proxy | **Verified** — `/api/health`, `/api/providers` and `/api/documents` all answered correctly via the dev server |
| Prefer-then-walk under real contention | **Verified** — `5000` and `8080` were both held by unrelated processes, so the launcher took `5001`/`8081` and the frontend followed with no manual step |
| Teardown releases the ports | **Verified** — after stop, neither `5001` nor `8081` held a LISTENING socket |
| SSE through the launcher (`POST /api/query`) | **Not verified** — needs a configured LLM provider; no `Backend/.env` exists, so `/api/providers` reports both providers unavailable |
| The reloader's double-load and port-holding behaviour (Decision 7, `dev.py:146-148`) | **Not verified — code-asserted** (`dev.py`'s own comments); the verifying run used `--no-reload`, which bypasses it |

The venv prerequisite is now **closed** — `Backend/.venv` exists and the launcher boots the backend end to
end. Two rows remain open, for unrelated reasons: SSE needs an API key, and the reloader path was
deliberately bypassed by `--no-reload` during the verifying run.

> [!NOTE]
> That install resolved `langchain 1.3.15` and `langgraph 1.2.11` against floors of `>=0.2.0` and
> `>=0.1.0` — major versions past what the pipeline was written for. It imports and builds the graph
> today, but `requirements.txt` carries no upper bounds, so a later fresh install can silently pull a
> breaking major.

Startup behaviour and the traps around it are documented in
[`../../../project-context/runtime/backend-startup/README.md`](../../../project-context/runtime/backend-startup/README.md);
the commands themselves in
[`../../../project-context/operations/run-and-build/README.md`](../../../project-context/operations/run-and-build/README.md).
