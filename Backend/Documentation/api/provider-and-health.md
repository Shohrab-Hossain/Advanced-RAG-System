<div align="center">

# 🩺 Provider & Health API

### The two smallest routes in the system — one of which quietly makes a network call and can block for ten seconds.

<br>

[![Routes](https://img.shields.io/badge/routes-2-1c7ed6)](#-1-the-two-routes)
[![Key exposure](https://img.shields.io/badge/API%20key-boolean%20only-3fb950)](#26-the-api-key-never-leaves-the-server)
[![Version](https://img.shields.io/badge/version-0.1.0-3fb950)](../../pyproject.toml)

[![Worst case](https://img.shields.io/badge/providers%20worst%20case-~10s-f59e0b)](#-4-performance)
[![Health](https://img.shields.io/badge/health-liveness%20only-f59e0b)](#35-liveness-not-readiness)
[![Auth](https://img.shields.io/badge/auth-none-ef4444)](#-7-security-notes)

</div>

<br>

---

<br>

## Content Tree

<pre>
Provider &amp; Health API
│
├── <a href="#-overview">📖 Overview</a>
│
├── <a href="#-1-the-two-routes">🧭 1. The two routes</a>
│
├── <a href="#-2-list-llm-providers">🔌 2. List LLM providers</a>
│   ├── <a href="#21-request">2.1 Request</a>
│   ├── <a href="#22-how-to-call">2.2 How to call</a>
│   ├── <a href="#23-success-response">2.3 Success response</a>
│   ├── <a href="#24-error-responses">2.4 Error responses</a>
│   ├── <a href="#25-field-by-field">2.5 Field by field</a>
│   ├── <a href="#26-the-api-key-never-leaves-the-server">2.6 The API key never leaves the server</a>
│   ├── <a href="#27-the-ollama-probe">2.7 The Ollama probe</a>
│   └── <a href="#28-the-hardcoded-openai-model-list">2.8 The hardcoded OpenAI model list</a>
│
├── <a href="#-3-health-check">🩺 3. Health check</a>
│   ├── <a href="#31-request">3.1 Request</a>
│   ├── <a href="#32-how-to-call">3.2 How to call</a>
│   ├── <a href="#33-success-response">3.3 Success response</a>
│   ├── <a href="#34-error-responses">3.4 Error responses</a>
│   └── <a href="#35-liveness-not-readiness">3.5 Liveness, not readiness</a>
│
├── <a href="#-4-performance">⏳ 4. Performance</a>
│
├── <a href="#%EF%B8%8F-5-edge-cases-and-gotchas">⚠️ 5. Edge cases and gotchas</a>
│
├── <a href="#-6-what-smoke-checks">🧪 6. What smoke checks</a>
│
├── <a href="#-7-security-notes">🔒 7. Security notes</a>
│
└── <a href="#-8-related-reading">🔗 8. Related reading</a>
</pre>

<br>

---

<br>

## 📖 Overview

Two routes remain after the query and knowledge-base surfaces: one tells a client **which LLM providers
are configured and usable**, the other tells an orchestrator **whether the Flask process is answering at
all**. They look like a matched pair of trivial GETs. They are not.

`GET /api/health` is 19 lines of file, one line of body, and touches nothing. `GET /api/providers` reads
four `Config` attributes and then **makes a live outbound HTTP call to the Ollama server**, which is the
only outbound call anywhere in this API and can hold the request open for roughly ten seconds.

> [!IMPORTANT]
> **Neither route is authenticated, and one of them is the sole guardian of the OpenAI API key's
> confidentiality.** `GET /api/providers` reports key presence as a **boolean and nothing else** — that
> single `bool()` call is the whole guarantee (§2.6). It must stay a boolean: any prefix, length hint,
> masked form or `key_set_at` timestamp added to that payload leaks material about a secret over an
> unauthenticated endpoint.

---

## 🧭 1. THE TWO ROUTES

| Method | Path | Handler | File:line | Blueprint | Outbound I/O |
|---|---|---|---|---|---|
| `GET` | `/api/providers` | `providers()` | `routes/provider/provider_routes.py:27` | `provider` | **yes** — probes Ollama |
| `GET` | `/api/health` | `health()` | `routes/health_check/health_check_routes.py:17` | `health_check` | none |

**Both always return `200`.** Neither handler has a validation branch, a parameter, or a `try` — there is
no error path in either one.

---

## 🔌 2. LIST LLM PROVIDERS

```text
GET /api/providers
```

Reports which chat providers exist, which models each offers, which is the default, and whether each is
currently usable.

**Auth:** none required — and none possible.

### 2.1 Request

No parameters, no headers, no body. Nothing about the request varies the response.

### 2.2 How to call

**cURL**

```bash
curl http://localhost:5000/api/providers
```

**JavaScript (fetch)**

```js
const { providers, default: defaultProvider } = await fetch(
  'http://localhost:5000/api/providers',
).then(r => r.json())

// `default` is a reserved word — destructure it under another name, as above.
const usable = providers.filter(p => p.available)
```

**Python (requests)**

```python
import requests

# Allow a generous read timeout: this route probes Ollama and can take ~10 s.
data = requests.get("http://localhost:5000/api/providers", timeout=(5, 15)).json()

for p in data["providers"]:
    print(p["id"], "available" if p["available"] else "unavailable", p["models"])
print("default:", data["default"])
```

### 2.3 Success response

**`200 OK`** — always. Two array entries plus a top-level default:

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
      "available": true,
      "models": ["llama3.2", "mistral"]
    }
  ],
  "default": "openai"
}
```

> [!NOTE]
> **The two entries are not the same shape.** `base_url` exists **only** on the Ollama entry
> (`provider_routes.py:44`). A client must not assume a uniform provider record — and the difference is
> not incidental: it exists because only Ollama has an address to talk to.

### 2.4 Error responses

**None.** The handler (`:27-50`) has no `try`, no validation and no failure branch. Even a completely
unreachable Ollama server produces a `200` — the failure is expressed as `available: false` inside the
body, not as a status code.

The only way to get a non-`200` from this path is a framework-level error: a `405` on a non-`GET` method,
or a `500` if something raised outside the handler. Both return **HTML**, not JSON, because there is no
`@app.errorhandler` anywhere — see [`README.md`](README.md) §7.2.

### 2.5 Field by field

| Field | Source | Notes |
|---|---|---|
| `providers[].id` | literal | `"openai"` \| `"ollama"` — the exact values `POST /api/query` accepts for `provider` |
| `providers[].label` | literal | `"OpenAI"` · `"Local (Ollama)"` — display text |
| `providers[0].model` | `Config.LLM_MODEL` (`config.py:25`) | default `gpt-4o-mini` |
| `providers[0].available` | **`bool(Config.OPENAI_API_KEY)`** (`:37`) | §2.6 |
| `providers[0].models` | `_OPENAI_MODELS` (`:17-22`) | a hardcoded four-item list — §2.8 |
| `providers[1].model` | `Config.OLLAMA_MODEL` (`config.py:29`) | default `llama3.2` |
| `providers[1].base_url` | `Config.OLLAMA_BASE_URL` | **only the Ollama entry carries this key** |
| `providers[1].available` | `check_ollama()["available"]` | a **live network probe**, per request — §2.7 |
| `providers[1].models` | `check_ollama().get("models", [])` | whatever the local server reports it has pulled |
| `default` | `Config.DEFAULT_PROVIDER` (`config.py:32`) | `"openai"` — what `POST /api/query` uses when the body omits `provider` |

**`model` versus `models` is the distinction most easily missed.** `model` is the *configured default* for
that provider — the one used when a query omits the `model` field. `models` is the *menu* a picker can
offer. Nothing reconciles the two: `Config.LLM_MODEL` may hold a value that does not appear in `models`.

### 2.6 The API key never leaves the server

The module docstring states the guarantee (`provider_routes.py:6-7`): *"The API key stays server-side:
availability is reported as a BOOLEAN and the key itself never enters the response."*

The mechanism is one expression:

```python
# routes/provider/provider_routes.py:37
"available": bool(Config.OPENAI_API_KEY),
```

**That `bool()` is the whole guarantee.** It collapses the secret to `true`/`false` before serialisation.
There is no prefix, no length, no masked form, no `key_set_at`. `OPENAI_API_KEY` appears **nowhere else
in any route file** — verified by grep across `routes/`.

Two honest caveats a client needs:

- **`available: true` means "a non-empty string is configured", not "the key works."** Nothing validates
  it against OpenAI. A revoked, expired or malformed key still reports `true`, and the failure surfaces
  much later as a `stage_error` frame inside a query stream ([`query.md`](query.md) §5.6).
- **The two `available` fields do not mean the same thing.** OpenAI's is a *configuration* check; Ollama's
  is a *network* check. A reader who assumes symmetry will read more into the OpenAI value than it
  carries.

### 2.7 The Ollama probe

`providers()` calls `check_ollama()` (`custom_packages/rag_pipeline/models/llm.py:102-136`) on **every
request**. It makes up to two attempts, each with `timeout=5`:

1. **`GET {base}/api/tags`** — on success returns
   `{"available": true, "models": [names], "base_url": base}` (`:114-118`).
2. **On failure, a bare root ping `GET {base}`** — any status below `500` returns
   `{"available": true, "models": [], "base_url": base, "warning": "Connected but could not list models"}`
   (`:127-132`).
3. **Otherwise** `{"available": false, "models": [], "error": "<detail>", "base_url": base}` (`:136`).

The probe uses `requests` rather than `urllib`, with the reason in its own docstring (`llm.py:105`):
*"more reliable on Windows than urllib."*

> [!WARNING]
> **The route drops the diagnostic detail.** `provider_routes.py:45-46` reads only `["available"]` and
> `.get("models", [])` — the `warning` and `error` keys `check_ollama()` produces are **never
> forwarded**. So a client cannot distinguish *"Ollama is up but could not list models"* from *"Ollama is
> up with zero models pulled"*: both appear identically as `available: true, models: []`. And when Ollama
> is down, the client sees `available: false` with no reason attached, even though the reason existed one
> stack frame earlier.

### 2.8 The hardcoded OpenAI model list

```python
# routes/provider/provider_routes.py:17
_OPENAI_MODELS = [
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-turbo",
    "gpt-3.5-turbo",
]
```

Not environment-driven, not fetched from OpenAI, not validated against anything. It exists to populate
the Configuration page's model picker, and **updating it is a code change.** A model OpenAI released
yesterday will not appear here; a model OpenAI retired will.

Its existence is also **corroborating evidence for a fact documented on the query page**: the request's
`model` field works for OpenAI, not only for Ollama. A picker built to feed an ignored field would be
pointless, and the frontend does feed it — see [`query.md`](query.md) §2.3, where the stale
`query_routes.py:48` comment claiming otherwise is set against `llm.py:62`, which uses the override in
the OpenAI branch.

`Config.LLM_MODEL` is not required to be in this list, and nothing reconciles the two.

---

## 🩺 3. HEALTH CHECK

```text
GET /api/health
```

Reports that the Flask process is accepting requests. **Auth:** none.

The whole file is 19 lines with no imports beyond Flask — the smallest module in the backend:

```python
# routes/health_check/health_check_routes.py:17
@health_check_bp.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"})
```

### 3.1 Request

No parameters, no headers, no body.

### 3.2 How to call

```bash
curl http://localhost:5000/api/health
```

```js
const ok = await fetch('http://localhost:5000/api/health')
  .then(r => r.ok)
  .catch(() => false)
```

```python
import requests

try:
    up = requests.get("http://localhost:5000/api/health", timeout=2).json()["status"] == "healthy"
except requests.RequestException:
    up = False
```

### 3.3 Success response

**`200 OK`**, with **exactly one key**:

```json
{ "status": "healthy" }
```

| Aspect | Reality |
|---|---|
| Keys | **one** — `status` |
| Value | the literal string `"healthy"` |
| Version field | **none** |
| Dependency checks | **none** — no store, no LLM, no disk, no registry |
| Timestamp / uptime | none |

> [!CAUTION]
> **Do not code against `{"status": "ok", "version": "1.0.0"}`.** The retired `Backend/Documentation/api.md`
> claimed that shape at `:250-253`, and both the value and the second key were fabricated. The route
> returns `{"status": "healthy"}` and has never returned a version. A client checking
> `status === 'ok'` reports the server down while it is up.

### 3.4 Error responses

**None.** There is no branch that can fail. If the process is running, this route answers `200`; if it is
not, the request does not connect at all — which is precisely the signal the route exists to provide.

### 3.5 Liveness, not readiness

The shallowness is deliberate, and the docstring says why (`health_check_routes.py:6-7`):

> *"Deliberately shallow: infra/dev.py polls this while the embedding and reranker models are still
> loading, so it must answer before the pipeline is usable."*

**This is a liveness probe, not a readiness probe.** A `200` proves the Flask process is accepting
requests. It proves **nothing** about whether a query would succeed:

| A `200` here does **not** tell you | Where to look instead |
|---|---|
| whether the embedding or reranker model has loaded | nothing exposes this; it is observable only as latency on the first query |
| whether a provider is configured or reachable | `GET /api/providers` (§2) |
| whether the corpus contains anything | `GET /api/documents` ([`knowledge-base.md`](knowledge-base.md) §3) |
| whether the stores loaded their pickles successfully | nothing exposes this — a failed pickle load resets that store to empty silently |

Deepening this route would break its one caller's contract. `infra/dev.py` polls it to decide when to
bring the frontend up, and it must answer *before* the pipeline is usable; a readiness check here would
stall the dev launcher for as long as model loading takes.

**The other consumer** is the browser's connection dot: `Frontend/src/shared/components/NavBar/NavBar.vue`
imports `healthCheck` from `ragApi.js` (`:111`) and calls it at `:142`. That import is the **one accepted
exception** to the frontend's *"components call store actions, not services"* convention — the reasoning
belongs in the frontend docs, not here.

---

## ⏳ 4. PERFORMANCE

| Route | Cost | Worst case |
|---|---|---|
| `GET /api/health` | one `jsonify` of a one-key dict | sub-millisecond |
| `GET /api/providers` | four `Config` reads **plus a live network probe** | **~10 seconds** |

> [!WARNING]
> **`GET /api/providers` is the only route in this API that makes an outbound network call, and it is not
> cheap.** `check_ollama()` runs two probes in series, each with `timeout=5`. When `OLLAMA_BASE_URL`
> points at a host that **blackholes** packets rather than refusing them, both timeouts run to completion
> and the request blocks for roughly **ten seconds** before returning a perfectly ordinary `200`.
>
> The normal "Ollama is not running" case is fast — a refused TCP connection fails immediately — so this
> is a tail-latency problem, not a typical-case one. But it is the reason a Configuration page can appear
> to hang, and it applies on **every** request: nothing is cached, and nothing is memoised between calls.

Practical consequences for a caller:

- **Set a read timeout above 10 seconds**, or accept that a client-side timeout will fire on the exact
  network conditions that this call exists to detect.
- **Do not poll this route.** It is a page-load lookup, not a monitor. For liveness, poll `/api/health`,
  which costs nothing.
- **Do not put it on a hot path.** One provider list per configuration screen is the intended usage.

---

## ⚠️ 5. EDGE CASES AND GOTCHAS

- **`available: true` for OpenAI is a configuration fact, not a working key** (§2.6). The first real
  signal of a bad key is a `stage_error` frame inside a query stream.
- **`available` means two different things across the two entries** — one is a `bool()` of a string, the
  other is the result of a network round trip. The payload gives no hint of the asymmetry.
- **`base_url` is present on Ollama only** (§2.3). Iterating `providers` and reading `p.base_url`
  yields `undefined` for OpenAI.
- **`default` is a reserved word in JavaScript.** Destructure it under another name.
- **Nothing here blocks a query.** Availability is advisory. A request naming `openai` with no key
  configured is accepted by `POST /api/query`, runs, and fails at the first LLM call — as an in-band
  `error` event on a `200`, not a rejection.
- **The provider list is static except for Ollama's `models`.** Adding a provider means editing three
  places: the validation tuple in `query_routes.py:45`, the factory branch in `models/llm.py`, and this
  route's response — see [`../llm-providers/README.md`](../llm-providers/README.md).
- **`/api/health` answers while the pipeline is still warming up** (§3.5). It is not a signal that a query
  will succeed.
- **A `405` from either route is HTML**, not JSON, because no error handler is registered
  ([`README.md`](README.md) §7.2).

---

## 🧪 6. WHAT SMOKE CHECKS

Both of these routes are covered by `infra/smoke.py` — which is **a dev tool, not a test suite**, and
says so itself (`smoke.py:9-10`).

| Method | Path | Expected | Keys asserted |
|---|---|---|---|
| `GET` | `/api/health` | `200` | `status` |
| `GET` | `/api/providers` | `200` | `providers`, `default` |

```bash
Backend/.venv/Scripts/python infra/smoke.py
```

It builds the app through `create_app()` and drives Flask's test client, binding no port and writing
nothing. Note what that means for `/api/providers`: the smoke run **does** perform the live Ollama probe,
so it inherits the same up-to-ten-second worst case (§4).

> [!NOTE]
> **This is not test coverage and must not be described as such.** It asserts that two routes answer and
> that two keys exist. It checks no value, no shape below the top level, and none of the behaviour
> documented on this page. The project has **no test framework** — no runner in either manifest, no
> `tests/` directory, no CI.

---

## 🔒 7. SECURITY NOTES

- **Neither route is authenticated.** Both are readable by anyone who can reach the port — see
  [`README.md`](README.md) §4.
- **The API key is reported as a boolean and never serialised** (§2.6). **Keep it that way.** This is the
  one place a secret comes anywhere near a response body, and the protection is a single `bool()` call
  that a well-meaning "help the user debug their key" change would remove.
- **`GET /api/providers` is a minor unauthenticated information disclosure.** It reveals which providers
  are configured, the configured default model for each, the Ollama base URL, and **the names of every
  model pulled on the local machine**. None of that is a secret, but it is host information available
  without a credential.
- **`GET /api/health` leaks nothing** — one hardcoded string, no environment, no version, no paths. Its
  minimalism is a security property as well as a design one.

The trust boundaries and the mitigation (bind to localhost) are in
[`../security.md`](../security.md#-1-the-trust-boundary-model); the boolean-availability invariant behind
the disclosure above is [§10 item 1](../security.md#-10-what-the-system-gets-right).

---

## 🔗 8. RELATED READING

- [`README.md`](README.md) — the route index, blueprint registration, CORS, and the API-wide error contract
- [`../llm-providers/README.md`](../llm-providers/README.md) — `get_llm()`, the provider factory, and `check_ollama()` in full
- [`query.md`](query.md) — where `provider` and `model` are consumed, and the `model` field's real scope
- [`../configuration.md`](../configuration.md) — `LLM_MODEL`, `OLLAMA_MODEL`, `OLLAMA_BASE_URL`, `DEFAULT_PROVIDER`, `OPENAI_API_KEY`
- [`knowledge-base.md`](knowledge-base.md) — the five knowledge-base routes
- [`../security.md`](../security.md) — trust boundaries and accepted risks
- [`../../../Frontend/Documentation/configuration-page/README.md`](../../../Frontend/Documentation/configuration-page/README.md) — the page that consumes this route, its 15-second poll, and the `error` key it expects but never receives
