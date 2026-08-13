# ADR-005: Dual LLM provider — OpenAI and Ollama, chosen per request
Date: 2026-08-13 · Status: accepted

> Reconstructed from the code on 2026-08-13, not recorded at decision time. Grounded in
> `rag_pipeline/encoding/llm.py`, the `/api/providers` and `/api/query` routes, and
> `Frontend/src/views/ConfigView.vue`.

## Context

The system sends the user's documents to a language model four times per query. That creates a hard
tradeoff the product surfaces explicitly in `ConfigView.vue`: OpenAI gives the best reasoning and
instruction-following but **sends the data to OpenAI's servers** and costs money per call; a local Ollama
model is **fully private and free** but its quality varies with model size.

Different users — and the same user on different documents — will resolve that tradeoff differently, and
they should not have to reconfigure or restart the server to do so.

## Decision

Support both providers behind a single factory, `get_llm(provider, temperature, json_mode, model)` in
`encoding/llm.py`, and select the provider **per request**: the `/api/query` body carries `provider` and an
optional `model`, which are validated in the route, carried on `RAGState`, and used by all four LLM nodes.
`/api/providers` reports live availability — OpenAI iff a key is configured, Ollama by probing
`{OLLAMA_BASE_URL}/api/tags` — so the UI can show what actually works right now.

Two supporting mechanisms make small local models viable:

- **`json_mode`** passes `format="json"` to `ChatOllama`, constraining the output; OpenAI needs no
  equivalent because parsing is handled downstream.
- **`safe_json_parse()`** recovers a JSON object from imperfect output in three escalating attempts: direct
  parse, then a ```` ```json ```` fence extraction, then the first `{...}` block.

Instances are cached by `(provider, temperature, json_mode, model)` to avoid building a new HTTP client on
every node call.

## Alternatives considered

- **OpenAI only** — rejected by the existence of the whole Ollama path; the privacy property is stated as a
  headline feature in the UI.
- **Ollama only** — rejected implicitly; `DEFAULT_PROVIDER` defaults to `openai` and the reasoning quality
  argument is stated in `ConfigView.vue`.
- **A build-time or env-only provider choice** — rejected in favour of a per-request field, which is why
  `provider` and `ollama_model` are carried on `RAGState` rather than read from `Config` inside the nodes.
- TODO: no record of whether other providers (Anthropic, local llama.cpp bindings, etc.) were considered.

## Consequences

**Makes easy**

- The whole system can run with **no data leaving the machine**, which is the difference between usable and
  unusable for sensitive documents.
- Switching providers or models is a UI toggle with no restart.
- One place constructs models, so credentials and provider quirks stay in one file.
- `safe_json_parse` makes the structured-output nodes tolerant of weaker models.

**Makes hard / watch out for**

- **Every structured prompt must work on both** a frontier model and a small local one — which is why the
  prompts carry explicit "Respond ONLY with valid JSON" instructions and inline examples.
- **The provider is fixed for the whole run.** All four calls use one provider; there is no per-node
  routing (e.g. a cheap model for planning, a strong one for reasoning).
- **The OpenAI model list is hardcoded in `app.py`** and does not reflect the account's real access; it
  goes stale as models change.
- **The LLM cache is never invalidated**, so a runtime env change does not reach an already-cached
  instance.
- **`get_llm` reads `LLM_MODEL`, `OLLAMA_MODEL`, and `OLLAMA_BASE_URL` from `os.getenv` directly**, not via
  `Config` — a second read path for the same values.
- **An unreachable Ollama server is only detected by the probe.** A query still starts and fails inside the
  first node, surfacing as a `stage_error` event rather than a clean rejection.
- **The field is named `ollama_model`** on `RAGState` but is applied to both providers — a naming trap.
