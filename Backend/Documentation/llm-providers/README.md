<div align="center">

# 🧠 LLM Providers

### One factory function, two providers, and a three-layer JSON discipline built so the same prompts survive both a frontier model and a small local one.

<br>

[![Providers](https://img.shields.io/badge/providers-OpenAI%20%2B%20Ollama-1c7ed6)](#-1-purpose--user-visible-behavior)
[![Construction points](https://img.shields.io/badge/construction%20points-1-7c5cff)](#51-get_llm--the-single-construction-point)
[![Version](https://img.shields.io/badge/version-0.1.0-3fb950)](../../pyproject.toml)

[![Temperature](https://img.shields.io/badge/temperature-0%20everywhere-f59e0b)](#42-what-is-fixed-for-a-whole-run)
[![JSON](https://img.shields.io/badge/JSON-prompt%20%2B%20format%20%2B%20salvage-f59e0b)](#53-the-three-layer-json-contract)
[![Key handling](https://img.shields.io/badge/API%20key-never%20leaves%20the%20server-3fb950)](#-6-wire-shape-cross-boundary-contracts)

</div>

<br>

---

<br>

## Content Tree

<pre>
LLM Providers
│
├── <a href="#-overview">📖 Overview</a>
│
├── <a href="#-1-purpose--user-visible-behavior">🎯 1. Purpose &amp; user-visible behavior</a>
│   ├── <a href="#11-choosing-a-provider-and-a-model">1.1 Choosing a provider and a model</a>
│   └── <a href="#12-what-available-actually-means">1.2 What "available" actually means</a>
│
├── <a href="#-2-where-it-lives">📍 2. Where it lives</a>
│
├── <a href="#%EF%B8%8F-3-architecture">🏗️ 3. Architecture</a>
│   ├── <a href="#31-three-public-functions-one-file">3.1 Three public functions, one file</a>
│   ├── <a href="#32-deferred-imports-and-the-instance-cache">3.2 Deferred imports and the instance cache</a>
│   └── <a href="#33-the-sibling-in-models-the-embedder">3.3 The sibling in models/: the embedder</a>
│
├── <a href="#-4-lifecycle--state-machine">🔄 4. Lifecycle &amp; state machine</a>
│   ├── <a href="#41-how-a-provider-is-chosen-and-pinned">4.1 How a provider is chosen and pinned</a>
│   ├── <a href="#42-what-is-fixed-for-a-whole-run">4.2 What is fixed for a whole run</a>
│   └── <a href="#43-how-credentials-actually-reach-openai">4.3 How credentials actually reach OpenAI</a>
│
├── <a href="#%EF%B8%8F-5-key-algorithms--data-structures">⚙️ 5. Key algorithms &amp; data structures</a>
│   ├── <a href="#51-get_llm--the-single-construction-point">5.1 get_llm — the single construction point</a>
│   ├── <a href="#52-safe_json_parse--the-salvage-parser">5.2 safe_json_parse — the salvage parser</a>
│   ├── <a href="#53-the-three-layer-json-contract">5.3 The three-layer JSON contract</a>
│   └── <a href="#54-check_ollama--the-two-probe-liveness-check">5.4 check_ollama — the two-probe liveness check</a>
│
├── <a href="#-6-wire-shape-cross-boundary-contracts">🔌 6. Wire shape (cross-boundary contracts)</a>
│
├── <a href="#%EF%B8%8F-7-edge-cases--gotchas">⚠️ 7. Edge cases &amp; gotchas</a>
│
├── <a href="#-8-failure-modes">💥 8. Failure modes</a>
│
├── <a href="#-9-extension-points">🧩 9. Extension points</a>
│
└── <a href="#-10-related-decisions--deeper-reading">🔗 10. Related decisions &amp; deeper reading</a>
</pre>

<br>

---

<br>

## 📖 Overview

Every chat model in this system is built by one function, `get_llm()`, in one file
(`custom_packages/rag_pipeline/models/llm.py`, 136 lines). Four pipeline nodes call it — planner,
compressor, reasoning, reflection — and none of them knows which provider it got. Provider selection,
model selection, credential handling and JSON-mode configuration all live behind that one call.

The system supports two providers and treats them as genuinely different machines rather than
interchangeable back ends: **OpenAI** (`ChatOpenAI`, a hosted frontier model) and **Ollama**
(`ChatOllama`, a local server, typically a much smaller model). Everything unusual about this module —
the prompt conventions, the salvage parser, the duplicated Ollama defaults — exists because the second
case is real.

> [!IMPORTANT]
> **`json_mode=True` does something on Ollama and nothing at all on OpenAI.** Ollama gets
> `format="json"`, a hard grammar constraint at the decode layer (`llm.py:47-48`). The OpenAI branch
> passes only `model` and `temperature` — **no `response_format`, no `.with_structured_output()`, no
> output parser** (`llm.py:60-64`). So on OpenAI, JSON discipline rests entirely on the prompt
> instruction plus `safe_json_parse`. The docstring at `llm.py:30` claims *"OpenAI: no change needed
> (JsonOutputParser handles it)"* — **no `JsonOutputParser` exists anywhere in this repository.** Trust
> the code.

---

## 🎯 1. PURPOSE & USER-VISIBLE BEHAVIOR

### 1.1 Choosing a provider and a model

The configuration page lists both providers with their status, and the chat page sends the chosen one
with every query. The request body is `{query, provider?, model?}`:

- **`provider`** is `"openai"` or `"ollama"`. Omitted, it falls back to `Config.DEFAULT_PROVIDER`
  (default `openai`, `query_routes.py:44`). Anything else is a `400`.
- **`model`** overrides the chat model by name.

> [!WARNING]
> **The `model` field is *not* Ollama-only, despite what the code comment says.**
> `query_routes.py:48` reads *"Optional model override (only meaningful for Ollama; ignored for
> OpenAI)"*, and the state key it feeds is named `ollama_model` (`:49`, `:58`). **Both the comment and
> the key name are wrong.** `get_llm`'s OpenAI branch uses the same parameter:
> `model=model or os.getenv("LLM_MODEL", "gpt-4o-mini")` (`llm.py:62`). So
> `{"provider": "openai", "model": "gpt-4o"}` genuinely switches the OpenAI model — and the frontend
> depends on it, sending `openaiModel.value` when the provider is `openai`
> (`Frontend/src/store/ragStore.js:133-134`) against the four-entry `_OPENAI_MODELS` list that
> `/api/providers` ships for the picker (`provider_routes.py:17-22`). **The behaviour is correct and is
> a shipped feature; only the naming is misleading.**

### 1.2 What "available" actually means

`GET /api/providers` reports each provider's usability, and the two are established very differently:

| Provider | `available` is | Cost of the check |
|---|---|---|
| OpenAI | `bool(Config.OPENAI_API_KEY)` — **a key is configured**, not that it works | free |
| Ollama | the result of a live HTTP probe against the Ollama server | up to **10 seconds** when unreachable (§5.4) |

So an OpenAI provider marked available may still fail on the first call with an authentication error:
nothing validates the key until a real request is made. And because the Ollama probe runs on every call
to `/api/providers`, the configuration page can take ten seconds to render when Ollama is installed in
the user's mind but not actually running.

**The key itself never enters a response.** `provider_routes.py:6-7` states the invariant in the module
docstring, and `:37` implements it as a `bool(...)` cast.

---

## 📍 2. WHERE IT LIVES

Paths are relative to the package root, `Backend/src/adrag/`.

| Concern | Path | Anchor |
|---|---|---|
| The factory | `custom_packages/rag_pipeline/models/llm.py:24` | `get_llm` |
| JSON salvage | `custom_packages/rag_pipeline/models/llm.py:70` | `safe_json_parse` |
| Ollama probe | `custom_packages/rag_pipeline/models/llm.py:102` | `check_ollama` |
| Instance cache | `custom_packages/rag_pipeline/models/llm.py:21` | `_llm_cache` |
| Embedding singleton | `custom_packages/rag_pipeline/models/embeddings.py:16` | `get_embedder` |
| Provider status route | `routes/provider/provider_routes.py:27` | `providers` |
| Provider validation | `routes/query/query_routes.py:44` | `query` |
| `.env` loading | `config.py:19` | `load_dotenv(_BACKEND_ROOT / ".env")` |

```text
custom_packages/rag_pipeline/models/
│
├── 📄 llm.py                  get_llm() · safe_json_parse() · check_ollama() — 136 lines
└── 📄 embeddings.py           get_embedder() — the shared SentenceTransformer, 21 lines
```

The four call sites live one directory over, in `custom_packages/rag_pipeline/generation/`:
`planner.py:61`, `compressor.py:75`, `reasoning.py:74`/`:86`/`:110`, `reflection.py:82`.

---

## 🏗️ 3. ARCHITECTURE

### 3.1 Three public functions, one file

| Function | Line | Returns | Used by |
|---|---|---|---|
| `get_llm(provider, temperature, json_mode, model)` | `:24-67` | a LangChain `BaseChatModel` | the four generation nodes |
| `safe_json_parse(text)` | `:70-99` | `dict`, or raises `ValueError` | planner, reasoning, reflection |
| `check_ollama()` | `:102-136` | a status `dict` | `GET /api/providers` **only** |

> [!NOTE]
> **`check_ollama` is never called by the pipeline.** The graph does not check whether Ollama is up
> before calling it — a run against a dead Ollama server fails at the first node, with the transport
> error surfacing as a `stage_error` and the planner's fallback taking over. The probe exists purely to
> populate the configuration page.

**Nothing in the codebase constructs a chat model outside `get_llm()`.** `ChatOpenAI` appears only at
`llm.py:60-64` and `ChatOllama` only at `llm.py:45-57`. That single-construction-point rule is what
makes provider selection, credential handling and caching one file's problem rather than four nodes'.

### 3.2 Deferred imports and the instance cache

Both provider SDKs are imported **inside their branch**, not at module scope:

```python
# custom_packages/rag_pipeline/models/llm.py:44
if provider == "ollama":
    from langchain_ollama import ChatOllama
    ...
else:
    # Default: openai
    from langchain_openai import ChatOpenAI
```

Importing the pipeline therefore pulls in neither SDK, and an installation that only ever uses Ollama
never imports `langchain_openai`. It also keeps process start-up fast, which matters because the module
is imported transitively by `app.py` at factory time.

The cache is a plain module dict:

```python
# custom_packages/rag_pipeline/models/llm.py:19
# Cache LLM instances — avoids creating a new httpx client on every pipeline node call.
# Key: (provider, temperature, json_mode). Env vars are fixed at startup.
_llm_cache: dict = {}
```

Its purpose is to avoid constructing a fresh HTTP client for every node of every query — four
constructions per pass, times every retry, times every concurrent request.

> [!NOTE]
> **The comment says the key is a 3-tuple; the code uses a 4-tuple.** `cache_key = (provider,
> temperature, json_mode, model)` (`llm.py:39`). The `model` component was added when the per-request
> model override landed and the comment was not updated. Describe the 4-tuple.

**The cache is never invalidated and never bounded.** Two consequences follow directly, and both are
covered in §7: a runtime environment change cannot reach an already-constructed instance, and a distinct
model name per request creates a new cached client that is never evicted.

### 3.3 The sibling in `models/`: the embedder

`models/embeddings.py` is 21 lines and follows the *opposite* import convention to `llm.py`:

```python
# custom_packages/rag_pipeline/models/embeddings.py:8
import os
from sentence_transformers import SentenceTransformer

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

_embedder: SentenceTransformer | None = None
```

The import is at **module scope**, so importing the pipeline pulls in `sentence_transformers` — a slow
import — even for a request that never embeds anything. The reranker defers its `CrossEncoder` import
(`reranker.py:23-31`); this module does not.

**Weight loading, however, is lazy.** `get_embedder()` (`:16-21`) constructs the `SentenceTransformer`
on first call and caches it in the module global, and `ChromaVectorStore.embedder` is a `@property` that
calls it (`vector_store.py:32-34`) — so the model downloads and loads on the first `add_documents` or
`search`, not at import. Embeddings are always computed in the application and passed to Chroma
explicitly (`vector_store.py:66`), so `EMBEDDING_MODEL` is authoritative and Chroma's own default
embedder is never used. The retrieval-side detail is in
[`../hybrid-retrieval/stores.md`](../hybrid-retrieval/stores.md).

> [!NOTE]
> **`_embedder: SentenceTransformer | None = None` is why this project needs Python 3.10.** It is a PEP
> 604 union evaluated at **module scope**, at runtime — and no file in the backend carries
> `from __future__ import annotations`. The other mandating site is `model: str | None` in `get_llm`'s
> signature (`llm.py:25`). On Python 3.9 both raise `TypeError` at import. `pyproject.toml` declares
> `requires-python = ">=3.10"` to match.

---

## 🔄 4. LIFECYCLE & STATE MACHINE

### 4.1 How a provider is chosen and pinned

1. **The request names it, or the config does.**
   `provider = body.get("provider", Config.DEFAULT_PROVIDER).lower().strip()` (`query_routes.py:44`).
2. **The route validates it.** Not in `("openai", "ollama")` → `400` (`:45-46`).
3. **It is seeded onto `RAGState`** as `provider` (`:57`) and **never rewritten by any node**.
4. **Every `get_llm` call reads it off the state.** All four call sites pass `state["provider"]`.
5. **`get_llm` normalises it again** — `provider = (provider or "openai").lower().strip()`
   (`llm.py:38`) — and anything that is not the literal `"ollama"` falls through to the OpenAI branch
   (`:58-59`). Since the route already rejected other values, this is a second line of defence, not the
   primary validation.

### 4.2 What is fixed for a whole run

| Fixed | Value | Why it matters |
|---|---|---|
| Provider | `state["provider"]`, seeded once | **There is no per-node routing** — the same model plans, compresses, generates and criticises |
| Model | `state["ollama_model"]`, seeded once | Applies to both providers (§1.1) |
| Temperature | **`0`** — the signature default at `llm.py:24` | **No call site ever passes `temperature`** |

The temperature consequence is larger than it looks. Because every call is deterministic and
`reflection_feedback` is never fed back into any prompt, a reflection retry re-runs an identical
pipeline over an identical corpus and produces an identical answer — which the critic then judges
identically. The retry budget only does real work when web-search escalation adds documents that were
not there before. That chain is worked through in
[`../rag-pipeline/README.md`](../rag-pipeline/README.md) §7.

**Up to four LLM calls per pass**, three of them mandatory: the planner, the reasoning node and the
reflection critic always run; compression only calls a model when the assembled context exceeds
`MAX_CONTEXT_CHARS`, which at the defaults is uncommon.

### 4.3 How credentials actually reach OpenAI

**`Config.OPENAI_API_KEY` is never passed to anything that makes an API call.** Its only consumer in the
entire backend is the availability boolean at `provider_routes.py:37`. The OpenAI branch of `get_llm`
constructs the client with two arguments and no credential:

```python
# custom_packages/rag_pipeline/models/llm.py:60
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(
    model=model or os.getenv("LLM_MODEL", "gpt-4o-mini"),
    temperature=temperature,
)
```

The real path is environmental:

```text
Backend/.env  →  load_dotenv(_BACKEND_ROOT / ".env")      [config.py:19]
              →  os.environ["OPENAI_API_KEY"]
              →  langchain_openai's own env read inside ChatOpenAI()   [llm.py:61-64]
```

Two consequences follow, and both are easy to get backwards:

- **A shell-exported variable beats `Backend/.env`.** `load_dotenv`'s `override` parameter defaults to
  `False` and `config.py:19` does not pass it, so anything already in the process environment wins.
  `infra/dev.py:265-269` relies on exactly this: it injects `PORT` and `FRONTEND_URL` into the child
  process environment precisely because they take precedence over the file.
- **The ordering only works because `config.py` is imported first.** The chain is
  `app.py:27` → `routes/` → `llm.py`, so `load_dotenv` has always run by the time a model is
  constructed. Import `llm.py` in isolation without touching `adrag.config` and `.env` is never loaded
  at all.

---

## ⚙️ 5. KEY ALGORITHMS & DATA STRUCTURES

### 5.1 `get_llm` — the single construction point

**The problem:** four nodes need chat models with different JSON requirements, against two providers
whose configuration surfaces have almost nothing in common, without any node learning which provider it
is talking to.

```python
# custom_packages/rag_pipeline/models/llm.py:24
def get_llm(provider: str = "openai", temperature: float = 0, json_mode: bool = False,
            model: str | None = None):
```

**The asymmetry that defines the module:**

| Provider | What `json_mode=True` does | Line |
|---|---|---|
| Ollama | `kwargs["format"] = "json"` passed to `ChatOllama` — a hard grammar constraint at the decode layer | `:47-48` |
| OpenAI | **nothing** — no `response_format`, no structured-output helper, no parser | `:58-64` |

Note that when `json_mode` is false the kwarg is **omitted entirely** rather than passed as `None`:
`kwargs` starts empty and `format` is only inserted inside the `if` (`llm.py:46-48`).

**Ollama's duplicated defaults are deliberate**, and the in-code comment records why:

```python
# custom_packages/rag_pipeline/models/llm.py:49
llm = ChatOllama(
    # Defaults mirror Config.OLLAMA_MODEL / OLLAMA_BASE_URL (config.py:22-23).
    # Without them an /api/query that omits "model" passes None to ChatOllama
    # and every LLM node fails pydantic validation.
    model=model or os.getenv("OLLAMA_MODEL", "llama3.2"),
    base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    temperature=temperature,
    **kwargs,
)
```

This is a duplicated default that exists for a stated reason, unlike the incidental duplications
catalogued in [`../configuration.md`](../configuration.md).

### 5.2 `safe_json_parse` — the salvage parser

**The problem:** three nodes need structured output, one provider gets no format constraint at all, and
small local models routinely wrap their JSON in markdown fences or surround it with prose.

Three escalating attempts, each swallowing only `json.JSONDecodeError`:

| # | Strategy | Line | Handles |
|---|---|---|---|
| 1 | `json.loads(text)` | `:78-81` | a well-behaved model |
| 2 | strip a fence — `` r"```(?:json)?\s*([\s\S]+?)\s*```" `` | `:84-89` | a fenced code block |
| 3 | first brace block — `r"\{[\s\S]+\}"` | `:92-97` | prose before or after the object |

All three failing raises
`ValueError(f"Could not extract valid JSON from LLM output: {text[:300]!r}")` (`:99`) — truncated to 300
characters so a log line stays readable. **That `ValueError` is what each node's `except Exception`
catches**, which is how a malformed LLM response becomes a `stage_error` frame and a graceful fallback
rather than a crash.

> [!NOTE]
> **Attempt 3's regex is greedy and unanchored.** On output containing two JSON objects it matches from
> the first `{` to the **last** `}` — spanning both — and `json.loads` then fails on the combined span.
> It is a best-effort salvage, not a parser, and it is correct to describe it that way.

### 5.3 The three-layer JSON contract

Three of the four LLM-calling nodes require JSON; the compressor does not. Every one of the three
carries the same prompt conventions:

| Node | Prompt constant | `json_mode` | Parsed by | Defaults on a missing key |
|---|---|---|---|---|
| `planner` | `_PLANNER_PROMPT` (`planner.py:18-46`) | ✅ (`:61`) | `safe_json_parse` (`:63`) | `retrieve=True`, `use_external=False`, `query_type="factual"` |
| `compressor` | `_COMPRESS_PROMPT` (`compressor.py:22-34`) | ❌ — plain text out | — | n/a |
| `reasoning` | `_REASONING_PROMPT` (`reasoning.py:19-40`) | ✅ (`:86`) | `safe_json_parse` (`:88`) | `answer="No answer generated."` |
| `reflection` | `_REFLECTION_PROMPT` (`reflection.py:23-50`) | ✅ (`:82`) | `safe_json_parse` (`:88`) | **`grounded=True`, `confidence=0.8`** |

**The house convention, present in all three JSON prompts and absent from the compressor's:**

1. A literal **"Respond ONLY with valid JSON"** instruction — `planner.py:38` (*"— no markdown, no extra
   text"*), `reasoning.py:31` (*"(no markdown fences)"*), `reflection.py:33`.
2. An **inline shape example** with `<bool>` / `<0.0-1.0>` placeholders, written with **doubled braces**
   `{{ }}` because `ChatPromptTemplate` treats a single brace as a variable.
3. A `ChatPromptTemplate.from_messages([("system", …), ("human", …)])` pair, invoked as an LCEL chain:
   `(_PROMPT | llm).invoke({...})`.
4. **`.content` read off the raw message and handed to `safe_json_parse`** — never a structured-output
   helper.

**Why belt and braces:** the prompt instruction is the only thing acting on OpenAI, `format="json"`
constrains Ollama's decoder, and `safe_json_parse` catches whatever both miss. **All three layers must
survive together.** Remove the prompt instruction and OpenAI degrades immediately; remove
`safe_json_parse` and a small local model that emits a fenced block breaks every JSON node.

> [!WARNING]
> **The reflection node's defaults make the critic fail *open*.** `grounded` defaults to **`True`** and
> `confidence` to `0.8` when the key is absent (`reflection.py:90-91`), so a response that parses
> successfully but omits the keys reads as *verified grounded*. That is a direct consequence of the
> parse contract: `safe_json_parse` guarantees a `dict`, not a shape, and nothing validates the shape
> afterwards. The full node behaviour is in [`../rag-pipeline/nodes.md`](../rag-pipeline/nodes.md).

### 5.4 `check_ollama` — the two-probe liveness check

**The problem:** the configuration page needs both *is Ollama running* and *which models does it have*,
and older Ollama versions answer the second question differently or not at all.

- **Probe 1** — `GET {base}/api/tags`, `timeout=5`, `raise_for_status()`, then
  `[m["name"] for m in data.get("models", [])]` → `{"available": True, "models": [...], "base_url"}`
  (`:113-118`). Distinct diagnostics are recorded for `ConnectionError` (*"is it running?"*), `Timeout`,
  and any other exception (`:119-124`).
- **Probe 2 (fallback)** — a bare `GET {base}`, `timeout=5`, accepting **any status below 500** as proof
  the server is up. Returns `available: True`, an **empty** model list, and
  `"warning": "Connected but could not list models"` (`:127-133`). The in-code comment names older
  Ollama versions as the reason.
- **Failure** — `{"available": False, "models": [], "error": detail, "base_url": base}` (`:136`).

`requests` is imported **inside the function** as `_req` (`:108`), and the base URL is read with a third
copy of the `OLLAMA_BASE_URL` default (`:110`).

**Worst-case latency is 10 seconds** — two five-second timeouts in series — on every `GET /api/providers`
when Ollama is unreachable, which is the common case for a user who has only ever used OpenAI.

---

## 🔌 6. WIRE SHAPE (CROSS-BOUNDARY CONTRACTS)

**Outbound** — the two providers this module talks to:

| Direction | Target | Transport | Credential | Configured by |
|---|---|---|---|---|
| Backend → OpenAI | OpenAI chat completions | HTTPS, via `langchain_openai` | `OPENAI_API_KEY` read from `os.environ` **by the SDK**, never passed as an argument | `LLM_MODEL`, or the request's `model` |
| Backend → Ollama | `{OLLAMA_BASE_URL}` chat endpoint | HTTP, via `langchain_ollama` | none | `OLLAMA_MODEL`, `OLLAMA_BASE_URL`, or the request's `model` |
| Backend → Ollama | `{OLLAMA_BASE_URL}/api/tags` then `{OLLAMA_BASE_URL}` | HTTP, via `requests`, 5 s each | none | `check_ollama` only |

**Inbound** — `GET /api/providers` (`provider_routes.py:27-50`):

```json
{
  "providers": [
    {
      "id": "openai",
      "label": "OpenAI",
      "model": "gpt-4o-mini",
      "available": true,
      "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]
    },
    {
      "id": "ollama",
      "label": "Local (Ollama)",
      "model": "llama3.2",
      "base_url": "http://localhost:11434",
      "available": false,
      "models": []
    }
  ],
  "default": "openai"
}
```

`_OPENAI_MODELS` is a **hardcoded four-entry list** (`provider_routes.py:17-22`) — it is not fetched
from OpenAI and does not track their catalogue. The Ollama `models` array is whatever the live probe
returned, so it reflects what is actually pulled on the machine.

> [!IMPORTANT]
> **The API key stays server-side, and this route is the boundary.** Availability is reported as a
> **boolean only**; the key never appears in any response, log line or error message this module
> produces. Changing `bool(Config.OPENAI_API_KEY)` to anything that reveals the value — a prefix, a
> length, a masked form — breaks the one security invariant this file has. See
> [`../security.md`](../security.md#-10-what-the-system-gets-right).

---

## ⚠️ 7. EDGE CASES & GOTCHAS

- **A runtime environment change cannot reach a cached instance.** `_llm_cache` is never invalidated
  (`llm.py:21`), and every default in this module is read with `os.getenv` at call time against an
  environment frozen when `config.py` ran `load_dotenv`. Editing `.env` while the server is running
  changes nothing, ever. Restart the process.

- **A per-request model name grows the cache without bound.** The cache key includes `model`
  (`llm.py:39`) and nothing evicts. A UI that let users type arbitrary Ollama model names would
  accumulate one client object per distinct string for the life of the process. With the current fixed
  pickers this is bounded in practice, not by design.

- **`temperature` is part of the cache key but no call site ever sets it.** Every entry in the cache is
  therefore a `temperature=0` instance. If you add a call that passes a temperature, it gets its own
  cache slot automatically — the key was built for that.

- **An unknown provider silently becomes OpenAI inside `get_llm`.** The `else` at `llm.py:58` has no
  validation. The route catches bad values first, so this only matters for a caller invoking the
  pipeline directly — a script, a test, `infra/smoke.py`-style tooling — where a typo'd provider will
  quietly try to reach OpenAI rather than failing loudly.

- **`OLLAMA_MODEL` disagrees cosmetically between the two files.** `config.py:29` and `llm.py:53` say
  `llama3.2`; `.env.example:11` says `llama3.2:latest`. Ollama resolves an untagged name to `:latest`,
  so both select the same model — but the two strings are not equal, which matters if anything ever
  compares them.

- **Nothing sets a timeout, retry policy or base URL for OpenAI.** `ChatOpenAI` receives only `model`
  and `temperature` (`llm.py:61-64`); everything else — timeouts, retries, `base_url`, organisation —
  is left to `langchain_openai`'s own defaults. An OpenAI-compatible gateway cannot be pointed at
  without editing this file.

- **Two docstrings in this file describe code that does not exist.** `llm.py:20` says the cache key is a
  3-tuple (it is 4); `llm.py:30` says a `JsonOutputParser` handles OpenAI's JSON (there is none — the
  same claim also appears at `reasoning.py:7`). Both are stale comments, not stale behaviour.

- **The provider is fixed for the whole run, including retries.** A reflection retry does not re-read
  the request and cannot switch providers. If the model is the problem, the retry has the same problem.

---

## 💥 8. FAILURE MODES

| Failure | Symptom | Behaviour |
|---|---|---|
| `OPENAI_API_KEY` unset, provider `openai` | `/api/providers` reports `available: false`; a query still runs and fails at the first node | Nothing blocks the request — availability is advisory only |
| Invalid API key | An authentication error from the SDK inside the planner | Planner catches it → `stage_error` → falls back to `retrieve=True, use_external=False, query_type="factual"`; the run continues and usually fails again downstream |
| Ollama not running, provider `ollama` | Connection error at the first node | Same shape: `stage_error` on `planner`, then the fallback decision |
| Ollama not running, `/api/providers` called | Up to a **10-second** page load, then `available: false` with a diagnostic `error` string | Two 5 s probes in series (§5.4) |
| Ollama reachable but `/api/tags` fails | `available: true`, empty `models`, `warning: "Connected but could not list models"` | The root-ping fallback |
| Model returns prose instead of JSON | `safe_json_parse` salvages it, or raises `ValueError` | The node's `except Exception` turns the `ValueError` into a `stage_error` and a degraded fallback |
| Model returns valid JSON with missing keys | **No error at all** | `.get(key, default)` applies the node's default — for reflection that means `grounded=True` (§5.3) |
| `model` names an Ollama model that is not pulled | Provider-level error at the first node | Nothing pre-validates the name against the probe's `models` list |

> [!NOTE]
> **A provider outage is never fatal to the request, only to its quality.** Every LLM-calling node
> catches its own exceptions and degrades — the planner to a default decision, the compressor to
> truncation, reasoning to a plainer second attempt then a fixed string, reflection to *fail-open*. The
> user gets a `200` with an answer of some kind and a trail of `stage_error` events. The per-node
> fallbacks are tabulated in [`../rag-pipeline/nodes.md`](../rag-pipeline/nodes.md).

---

## 🧩 9. EXTENSION POINTS

**Add a provider.** Add a branch to `get_llm` (`llm.py:44-64`) with its import deferred inside the
branch, decide what `json_mode` should mean for it, and add its literal to the route's validation tuple
(`query_routes.py:45`). Then add an entry to `/api/providers` (`provider_routes.py:31-49`) so the picker
can offer it. Nothing else in the pipeline changes — the nodes only ever see the string on `RAGState`.

**Add a structured-output node.** Follow the three-layer convention exactly: a `_<NAME>_PROMPT` module
constant carrying the literal *"Respond ONLY with valid JSON"* instruction and a doubled-brace shape
example, `get_llm(provider, json_mode=True, model=ollama_model)`, and `safe_json_parse(response.content)`
inside a `try`. Choose your `.get(key, default)` defaults with the fail-open/fail-closed question in
mind — reflection's choice is a real behavioural decision, not a formality.

**Make the model configurable per node.** Every call site currently passes `state["ollama_model"]`.
Per-node routing would mean new `RAGState` keys and new seeds in `query_routes.py:54-79`; the cache
already keys on `model`, so it needs no change.

**Give OpenAI a real JSON mode.** The hook is the `else` branch at `llm.py:58-64` — adding
`model_kwargs={"response_format": {"type": "json_object"}}` or `.with_structured_output(...)` would make
the OpenAI path symmetric with Ollama's. **Keep the prompt instruction and `safe_json_parse` anyway**;
they are what makes the small-model path work, and removing either to celebrate the new constraint
breaks Ollama.

**What not to touch.** Do not construct a chat model outside `get_llm` — provider selection and
credential handling stay in one file. Do not pass `Config.OPENAI_API_KEY` into `ChatOpenAI` "for
clarity"; the SDK's own environment read is the working path, and adding an argument creates a second
one to keep correct. Do not expose anything but a boolean from `/api/providers`. Do not remove the
duplicated Ollama defaults at `llm.py:53-54` — a request without a `model` would pass `None` to
`ChatOllama` and every LLM node would fail pydantic validation.

---

## 🔗 10. RELATED DECISIONS & DEEPER READING

- **One factory function instead of a provider abstraction.** There is no `Provider` base class, no
  registry and no strategy object — just an `if`/`else` and a cache. For two providers whose only
  variable surface is *model name, base URL, and one JSON kwarg*, an abstraction would be more code
  describing less. The cost is that adding a third provider means editing this function rather than
  registering something, which is a fair trade at two.

- **Two providers of genuinely different capability, treated identically by the pipeline.** The whole
  point of supporting Ollama is that the system runs with no API key and no network. Every design choice
  in this module follows from refusing to assume the frontier-model behaviour: no native JSON mode is
  relied on, no response is trusted to parse, and every structured prompt carries its own shape example.
  A system that only ever had to satisfy OpenAI would not need `safe_json_parse` at all.

- **Credentials by environment rather than by argument.** Letting `langchain_openai` read
  `OPENAI_API_KEY` from `os.environ` keeps the secret out of every call signature, every traceback frame
  and every cache key. The trade is that the credential path is invisible in the code — which is exactly
  why it is written out in §4.3 — and that a shell export silently outranks the `.env` file people
  expect to be authoritative.

- **`temperature=0` by omission rather than by decision.** Nobody chose determinism explicitly; every
  call site simply declined to pass a temperature and inherited the signature default. The consequence
  is load-bearing anyway — it is one of the three facts that make a non-escalating retry pointless — so
  it is worth treating as a decision even though it was not recorded as one.

**Continue reading:**

- [`../rag-pipeline/README.md`](../rag-pipeline/README.md) — the pipeline that makes all four calls
- [`../rag-pipeline/nodes.md`](../rag-pipeline/nodes.md) — the four LLM-calling nodes, prompt by prompt
- [`../configuration.md`](../configuration.md) — every model, key and URL setting, with its real default
- [`../api/provider-and-health.md`](../api/provider-and-health.md) — `GET /api/providers` in full
- [`../security.md`](../security.md) — the key-stays-server-side invariant and the accepted prompt-injection risk
- [`../../../Frontend/Documentation/configuration-page/README.md`](../../../Frontend/Documentation/configuration-page/README.md) — how a user picks the provider and model this factory receives
