# Feature: LLM provider selection

**Purpose:** let the user pick between OpenAI and a locally-run Ollama model per query — the privacy/cost
tradeoff — without restarting or reconfiguring the server.

**Entry points:** the `/configuration` route (`ConfigView.vue` → `LLMSelector.vue`), the model label in
`NavBar.vue`, and the `provider` + `model` fields on every `POST /api/query` body.

**Implemented in:**

| Concern | File |
|---|---|
| Model construction + cache | `Backend/src/rag_pipeline/encoding/llm.py` → `get_llm()` |
| Ollama probe | `Backend/src/rag_pipeline/encoding/llm.py` → `check_ollama()` |
| Availability endpoint | `Backend/src/app.py` → `GET /api/providers` |
| Per-run propagation | `RAGState.provider`, `RAGState.ollama_model` |
| Selection UI | `Frontend/src/pages/configuration/components/LLMSelector/LLMSelector.vue`, `Frontend/src/pages/configuration/views/ConfigView.vue` |
| Client state | `Frontend/src/subsystems/rag/ragStore.js:32-38` → `llmProvider`, `ollamaModel`, `openaiModel`, `availableProviders`; `fetchProviders()` at `:200-219` |
| Availability fetch | `Frontend/src/subsystems/rag/ragApi.js:23` → `getProviders()` |
| Active-model badge | `Frontend/src/shared/components/NavBar/NavBar.vue:44-61`, computed at `:131-138` |

**Why the client half lives in the `rag` subsystem, not a `configuration` one:** the provider is not a
setting the app stores, it is a **field on every query** — `runQuery` reads `llmProvider` / `ollamaModel` /
`openaiModel` and puts them on the `POST /api/query` body (`ragStore.js:128-131` → `ragApi.js:42-43`). The
selector is a UI over the RAG store, so `getProviders` sits beside `streamQuery` in `ragApi.js` and
`kbApi.js` never learns the provider exists.

**Inputs:** a provider id (`"openai"` | `"ollama"`) and an optional model name.
**Outputs:** every LLM-calling node in the run uses that provider/model.

**Behaviour:**

- `GET /api/providers` returns both providers with `available` booleans. OpenAI is available iff
  `Config.OPENAI_API_KEY` is non-empty, and advertises a **hardcoded** model list:
  `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`, `gpt-3.5-turbo`. Ollama's availability and model list come from a
  live probe.
- `check_ollama()` does a two-step probe: `GET {OLLAMA_BASE_URL}/api/tags` for the real model list; on
  failure, a bare root ping — any status `< 500` counts as "up" with an empty list and a
  `"Connected but could not list models"` warning. Both failures return `{available: false, error: <detail>}`.
  It uses `requests` rather than `urllib`, noted in the code as more reliable on Windows.
- `/api/query` validates `provider` against `("openai", "ollama")` → `400` otherwise, and accepts an
  optional `model` override. That override is meaningful for Ollama; for OpenAI, `get_llm` also honours it
  (falling back to `LLM_MODEL`).
- `get_llm(provider, temperature=0, json_mode=False, model=None)` caches instances keyed by
  `(provider, temperature, json_mode, model)` — the docstring's stated reason is to avoid creating a new
  httpx client on every node call. For Ollama, `json_mode=True` passes `format="json"` to constrain output;
  for OpenAI no change is needed because parsing is handled downstream.
- `safe_json_parse()` recovers JSON from model output in three escalating attempts: direct
  `json.loads`, a ```` ```json ```` fence extraction, then the first `{...}` block. It raises `ValueError`
  with a 300-char excerpt if all three fail — this is what makes smaller local models usable.
- `LLMSelector.vue` fetches providers on mount and **polls every 15 seconds while Ollama is unavailable**
  (`:196-200`), stopping the interval on unmount (`:203`). Picking a provider also pre-selects a model when
  none is chosen yet (`select()`, `:187-191`). `fetchProviders()` in the store auto-selects the server's
  `default` provider if available, else the first available one, and pre-selects the server's default
  OpenAI model.
- `NavBar.vue` shows the resolved active model as a badge, falling back through
  *user choice → server default → first listed* (`activeModel`, `:131-138`), and swaps it for an amber
  "No API key" warning when OpenAI is selected but unavailable (`:44-52`).
- `ConfigView.vue` presents the tradeoff as fixed pro/con lists (`:125-137`): OpenAI — best reasoning, cost-effective
  `gpt-4o-mini`, but needs `OPENAI_API_KEY` and sends data to OpenAI; Ollama — fully private, no API costs,
  but needs Ollama running and quality varies by model size (7B+ recommended).

**Depends on:** `Config.OPENAI_API_KEY`, `Config.OLLAMA_BASE_URL`, `Config.OLLAMA_MODEL`,
`Config.LLM_MODEL`, `Config.DEFAULT_PROVIDER`. Consumed by every LLM node in
[`self-rag-pipeline`](../self-rag-pipeline/README.md).

**Gotchas:**

- **The OpenAI model list is hardcoded in `app.py`** — it does not reflect the account's actual access and
  goes stale as models change.
- **The provider is fixed for the whole run.** All four LLM calls use the same provider; there is no
  per-node model routing.
- **`get_llm` reads `OLLAMA_MODEL`, `OLLAMA_BASE_URL`, and `LLM_MODEL` from `os.getenv` directly**, not from
  `Config` — same values, but a second read path.
- **The LLM cache is never invalidated.** Changing an env var at runtime does not affect already-cached
  instances.
- **An unreachable Ollama server does not fail the request until a node actually calls it** — the probe only
  informs the UI.
