<div align="center">

<img src="https://api.iconify.design/ph/bug-beetle-fill.svg?color=%237c5cff&height=56" alt="Issues log" height="56" />

# Issues Log (ClaudeSH)

### Notable problems this kit hit and how they were solved — the postmortems behind the changelog.

</div>

<br>

> Newest first. Each entry is a small postmortem (symptom → root cause → fix → why → takeaway), stored
> under `entries/YYYY-MM-DD/`. The `#` column is a monotonic serial (1 = oldest); a new entry takes
> `max(#) + 1`. **This index is GENERATED** from each entry's frontmatter by
> `scripts/issues-index.py --render` -- never hand-written, so a row cannot disagree with its entry. See the
> [`csh-issues-logging`](../../../.claude/skills/csh-issues-logging/SKILL.md) skill for the format.

<br>

| #&nbsp; | Date | Time | Issue | Category |
|---|---|---|---|---|
| `3` | `2026-08-13` | `18:19` | [**`.md` uploads are advertised, accepted, then fail at ingest — the `markdown` package is missing from `requirements.txt`.** `md` is in `Config.ALLOWED_EXTENSIONS` (`config.py:63`) and the UI lists Markdown in its drop-zone copy and `accept` attribute, so the route's `_allowed()` check passes and the file is saved; the loader then raises `No module named 'markdown'` and `POST /api/upload` returns `{"error": "No module named 'markdown'"}`. The dependency is a transitive requirement of `unstructured`'s Markdown partitioner and is not declared anywhere — `Backend/requirements.txt` lists `unstructured>=0.14.0` but none of its per-format extras. The failure is a **runtime** one on a format the system claims to support, and it surfaces as an import error rather than an unsupported-type message, so it reads as a crash rather than a setup gap. **OPEN — not fixed** (found while seeding the knowledge base to verify a frontend refactor; `Backend/` was out of that plan's scope). Takeaway: an extension allow-list is a promise about capability, and it is validated independently of the loaders that must honour it — nothing ties the two together, so a format can be advertised in three places while being installable in none.](entries/2026-08-13/181930-md-upload-accepted-then-fails-missing-markdown-dep.md) | `dependency` |
| `2` | `2026-08-13` | `18:19` | [**Every LLM node fails validation on an Ollama request that omits `model`, because `get_llm()` has no fallback for `OLLAMA_MODEL`.** `encoding/llm.py:50` reads `model=model or os.getenv("OLLAMA_MODEL")` — **no default argument** — while the OpenAI branch eight lines below reads `os.getenv("LLM_MODEL", "gpt-4o-mini")` **with** one. The function's own docstring promises *"Falls back to the env-var default if not supplied"*, and `CLAUDE.md` documents `OLLAMA_MODEL`'s default as `llama3.2`, so both the code's contract and the docs claim a fallback that does not exist. Without a `.env`, `POST /api/query` with `{"provider":"ollama"}` and no `model` passes `None` into `ChatOllama` and pydantic rejects it — `planner`, `reasoning` and `reflection` all emit `stage_error` while retrieval, reranking and compression succeed, so the run *looks* half-working rather than misconfigured. **OPEN — not fixed** (found incidentally while smoke-testing the frontend refactor; `Backend/` was out of that plan's scope). Takeaway: when two branches of one factory read the same kind of setting, an inline default on one and not the other is a silent asymmetry — the docstring described the branch that had it.](entries/2026-08-13/181900-ollama-model-none-no-env-default.md) | `config` |
| `1` | `2026-08-13` | `10:11` | [**The frontend's `retry` SSE handler is unreachable dead code, so the reflection retry counter never moves.** `_applyEvent` in `subsystems/rag/ragStore.js` (was `stores/rag.js` when filed) guards every event with `if (!stage || !(stage in stageStatuses)) return`, but the backend's `retry` frame (`reflection.py:129-135`) carries `attempt`/`max_attempts`/`reason`/`escalate_external`/`message` and **no `stage` key** — so the guard returns before `case 'retry'` at `ragStore.js:109` can run. `retryCount` stays 0 and the retrieval stages never reset to idle, meaning a self-reflection retry is invisible in the UI even though the pipeline genuinely re-ran. **OPEN — not fixed.** Found by documentation ground-truthing, not by a bug report. Takeaway: a payload-shape assumption applied as a blanket guard silently disables every event that legitimately lacks that field.](entries/2026-08-13/101128-sse-retry-event-dropped-by-stage-guard.md) | `logic` |
