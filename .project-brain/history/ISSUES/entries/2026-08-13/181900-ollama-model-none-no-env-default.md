---
id: 2
date: 2026-08-13
time: "18:19"
category: config
summary: |-
  **Every LLM node fails validation on an Ollama request that omits `model`, because `get_llm()` has no fallback for `OLLAMA_MODEL`.** `encoding/llm.py:50` reads `model=model or os.getenv("OLLAMA_MODEL")` — **no default argument** — while the OpenAI branch eight lines below reads `os.getenv("LLM_MODEL", "gpt-4o-mini")` **with** one. The function's own docstring promises *"Falls back to the env-var default if not supplied"*, and `CLAUDE.md` documents `OLLAMA_MODEL`'s default as `llama3.2`, so both the code's contract and the docs claim a fallback that does not exist. Without a `.env`, `POST /api/query` with `{"provider":"ollama"}` and no `model` passes `None` into `ChatOllama` and pydantic rejects it — `planner`, `reasoning` and `reflection` all emit `stage_error` while retrieval, reranking and compression succeed, so the run *looks* half-working rather than misconfigured. **OPEN — not fixed** (found incidentally while smoke-testing the frontend refactor; `Backend/` was out of that plan's scope). Takeaway: when two branches of one factory read the same kind of setting, an inline default on one and not the other is a silent asymmetry — the docstring described the branch that had it.
---

# Ollama requests without an explicit `model` fail every LLM node

**Date:** 2026-08-13 · **Category:** config · **Status:** OPEN — diagnosed, not fixed
**Refs:** `Backend/src/rag_pipeline/encoding/llm.py:44-63`, `Backend/src/config.py`, `.claude/CLAUDE.md` (Models table)

## Symptom

A query issued against Ollama without naming a model returns a `200` with a completed pipeline that
has three broken stages:

```
stage_start planner    → stage_error planner
stage_start retrieval  → retrieval_result       ✓
stage_skip  external_tools                      ✓
stage_start aggregator → stage_complete         ✓
stage_start reranker   → stage_complete         ✓
stage_start compressor → stage_complete         ✓
stage_start reasoning  → stage_error reasoning
stage_start reflection → stage_error reflection
```

Each error carries the same text:

```
1 validation error for ChatOllama
model
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
```

The three failing nodes are exactly the three that call an LLM. Everything that only touches the
retrieval stores works, which is what makes this read as a partial outage rather than a config gap.

Reproduce with no `Backend/.env` present:

```bash
curl -N -X POST localhost:5000/api/query -H 'Content-Type: application/json' \
     -d '{"query":"anything","provider":"ollama"}'
```

Adding `"model":"llama3.2:latest"` makes the same request succeed end to end.

## Root cause

`get_llm()` builds the two providers asymmetrically (`encoding/llm.py:44-61`):

```python
if provider == "ollama":
    llm = ChatOllama(
        model=model or os.getenv("OLLAMA_MODEL"),        # ← no default
        base_url=os.getenv("OLLAMA_BASE_URL"),           # ← no default either
        ...
    )
else:
    llm = ChatOpenAI(
        model=model or os.getenv("LLM_MODEL", "gpt-4o-mini"),   # ← has one
        ...
    )
```

`os.getenv("OLLAMA_MODEL")` returns `None` when the variable is unset. `.env.example` sets it, so
anyone who followed the documented setup (`cp .env.example .env`) never sees this — it only bites a
run started without a `.env`, which is exactly the state a fresh clone or a quick `python dev.py` is in.

Two things actively assert the fallback exists:

- the docstring at `llm.py:33-34` — *"model: optional override for the model name… Falls back to the
  env-var default if not supplied."*
- `CLAUDE.md`'s Models table — *"Ollama chat model | `llama3.2` (`OLLAMA_MODEL`…)"*.

Both describe the OpenAI branch's behaviour and were written as though it were uniform.

The frontend hides the bug in normal use: `ragStore.runQuery` always sends a model, taken from
`ollamaModel` or the first entry of the provider's model list. So the failure surfaces only through a
direct API call — a curl, a Postman collection, an integration test.

## Proposed fix (not yet applied)

Give the Ollama branch the same inline defaults the OpenAI branch has, matching the values `config.py`
and `.env.example` already document:

```python
model=model or os.getenv("OLLAMA_MODEL", "llama3.2"),
base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
```

This also matches the project's stated convention — *"Config is read as `os.getenv("NAME", "<default>")`
with the default at the call site"*.

**Do not** fix it by making the route reject a request with no `model`. The API deliberately treats
`model` as optional (the `/api/query` contract and `streamQuery`'s signature both default it to
`None`), and a required field would be a breaking change to paper over a missing default.

## Why that works (and what didn't)

The failure is a missing default, not a missing validation. Supplying it restores the behaviour both
the docstring and the brief already promise, and does it in the one file that is allowed to construct
an LLM (ADR-005: *"Nothing constructs an LLM outside `get_llm()`"*), so there is exactly one place to
change.

**Ruled out — defaulting inside `ChatOllama`'s caller (the nodes).** Four nodes call `get_llm()`; a
default at each call site is four copies of one fact and re-opens the door for a fifth node to forget
it. The whole point of the factory is that provider details live in one file.

**Ruled out — reading `Config.OLLAMA_MODEL` instead of `os.getenv`.** It would work, but `llm.py`
deliberately reads the environment directly rather than importing `Config`, and changing that here
would make one setting follow a different path from its neighbours in the same function.

## Takeaway

When one function constructs two variants of the same thing from the same kind of setting, the
defaults must be symmetric or the asymmetry is invisible — nobody reads two branches side by side
looking for a missing second argument. The docstring here was not wrong when written about one
branch; it became wrong by being read as describing the function.

Corollary: a bug that only appears without a `.env` is one the documented setup path cannot find. The
smoke test that caught it was a bare `curl` against a `dev.py` run, which is the configuration a new
contributor actually starts from.
