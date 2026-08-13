# 🚀 Operations

How adRAG is configured, built, and run. It is a **local development system**: there is no deployment
pipeline, container image, CI configuration, or infrastructure code in the repository.

<br>

---

<br>

## Index

| Topic | Holds |
|---|---|
| [`configuration/`](configuration/README.md) | Every environment variable on both sides, its default, what it does, and the on-disk storage layout |
| [`run-and-build/`](run-and-build/README.md) | Prerequisites, install, the `python dev.py` launcher and its flags, the per-half fallback commands, the production build, and first-run behaviour |

<br>

---

<br>

## Ports

| Service | Port | Set in |
|---|---|---|
| Flask API | **5001** default (`.env.example:48` sets `5000`) | `PORT` env var → `Config.PORT` (`config.py:68`) |
| Vue dev server | 8080 | `Frontend/vue.config.js:7` `devServer.port` |
| Ollama (external) | 11434 | `OLLAMA_BASE_URL` (`config.py:22`) |

**Neither app port is fixed under the launcher.** `dev.py` probes for a free port before spawning — walking
upward from a base of `5000` for the API and `8080` for the UI across a 40-port span (`dev.py:36-40`,
`dev.py:70-89`, `dev.py:221-222`) — then injects the API port as `PORT` into the backend child
(`dev.py:231`) and pins the UI with `npm run serve -- --port <n>` (`dev.py:259`). Both are printed at
launch (`dev.py:248-249`); `--api-port` / `--ui-port` override the probe.

`Backend/.env.example` sets `FRONTEND_URL=http://localhost:5173` while the dev server actually runs on
8080. Standalone, the CORS allowlist in `app.py:44` covers the gap — it carries six entries
(`Config.FRONTEND_URL`, `:3000`, `:5000`, `:8080`, `:8081`, and a literal `"*"`; see
[`../security/trust-boundaries/README.md`](../security/trust-boundaries/README.md) for why that last entry
matters). Under `dev.py` the mismatch does not arise at all: `FRONTEND_URL` is injected as the real UI URL
(`dev.py:232`).

<br>

## Monitoring and logs

There is no logging configuration, log file, or metrics endpoint. `Backend/src/main.py` **reduces** output:
it sets `sentence_transformers` and `huggingface_hub` loggers to `ERROR` and filters five warning
patterns. Diagnostics are the console output plus `GET /api/health`.

TODO: no deployment target, process manager, backup policy, or monitoring stack is recorded anywhere in
the repository. Confirm with the owner before assuming any.
