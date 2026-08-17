<div align="center">

# ⚡ Configuration Page

### Pick a provider and a model, watch a 15-second liveness poll, and never see the panel that was written for when Ollama is down.

<br>

[![Components](https://img.shields.io/badge/components-1-1c7ed6)](#-2-where-it-lives)
[![Providers](https://img.shields.io/badge/providers-OpenAI%20%2B%20Ollama-7c5cff)](#-1-purpose--user-visible-behavior)
[![Manifest](https://img.shields.io/badge/manifest-package.json-3fb950)](../../package.json)

[![Poll interval](https://img.shields.io/badge/poll-15s%20while%20offline-f59e0b)](#42-the-polling-loop)
[![Model override](https://img.shields.io/badge/model%20field-both%20providers-3fb950)](#53-the-model-field-applies-to-both-providers)
[![Dead branch](https://img.shields.io/badge/unreachable%20UI-1%20panel-ef4444)](#71-the-cannot-reach-ollama-panel-can-never-render)

</div>

<br>

---

<br>

## Content Tree

<pre>
Configuration Page
│
├── <a href="#-overview">📖 Overview</a>
│
├── <a href="#-1-purpose--user-visible-behavior">🎯 1. Purpose &amp; user-visible behavior</a>
│
├── <a href="#-2-where-it-lives">📍 2. Where it lives</a>
│
├── <a href="#%EF%B8%8F-3-architecture">🏗️ 3. Architecture</a>
│   ├── <a href="#31-two-halves-one-store">3.1 Two halves, one store</a>
│   └── <a href="#32-derived-state">3.2 Derived state</a>
│
├── <a href="#-4-lifecycle--state-machine">🔄 4. Lifecycle &amp; state machine</a>
│   ├── <a href="#41-mount-and-first-fetch">4.1 Mount and first fetch</a>
│   ├── <a href="#42-the-polling-loop">4.2 The polling loop</a>
│   └── <a href="#43-choosing-a-provider">4.3 Choosing a provider</a>
│
├── <a href="#%EF%B8%8F-5-key-algorithms--data-structures">⚙️ 5. Key algorithms &amp; data structures</a>
│   ├── <a href="#51-the-two-fallback-chains">5.1 The two fallback chains</a>
│   ├── <a href="#52-the-model-pickers">5.2 The model pickers</a>
│   └── <a href="#53-the-model-field-applies-to-both-providers">5.3 The model field applies to both providers</a>
│
├── <a href="#-6-wire-shape-cross-boundary-contracts">🔌 6. Wire shape (cross-boundary contracts)</a>
│
├── <a href="#%EF%B8%8F-7-edge-cases--gotchas">⚠️ 7. Edge cases &amp; gotchas</a>
│   └── <a href="#71-the-cannot-reach-ollama-panel-can-never-render">7.1 The "Cannot reach Ollama" panel can never render</a>
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

The configuration page chooses which LLM answers the next query. It is the only page whose folder holds
exactly one component: `ConfigView.vue` (138 lines) laid out beside `LLMSelector.vue` (204 lines).

The division is clean. **`ConfigView` is static explanation** — two informational cards comparing the
providers, plus a Quick Start block for getting Ollama running. **`LLMSelector` is the interactive
half** — provider buttons, model pickers, a manual refresh, and a background poll that keeps checking
whether a local Ollama server has come up.

Neither component talks to the network directly. Both read `useRagStore`, and the store's
`fetchProviders()` is the single path to `GET /api/providers`.

This page also carries the codebase's one genuinely unreachable UI branch, documented in §7.1 as a
limitation rather than swept under the rug.

---

## 🎯 1. PURPOSE & USER-VISIBLE BEHAVIOR

The user arrives to two provider cards on the left and two explanation cards on the right.

**OpenAI** shows `✓ Ready` when the server holds an API key, or `⚠ No key` when it does not. **Ollama**
shows `✓ Running` or `✗ Offline` depending on whether the backend could reach a local Ollama server.
Selecting an available provider immediately becomes the provider for the next query — there is no Save
button, because the selection is store state, not a form.

Choosing a model is a **list of buttons**, not a dropdown. Each row shows a dot, the model name in
monospace, and an "active" pill on the current choice.

If Ollama is offline, a **Quick Start** block appears with the two commands that fix it:

```bash
ollama serve
ollama pull llama3.2
```

The two informational cards are hardcoded, four items each:

| OpenAI | Ollama |
|---|---|
| ✓ Best reasoning and instruction following | ✓ Fully private — no data leaves your machine |
| ✓ `gpt-4o-mini` is fast and cost-effective | ✓ No API costs — unlimited queries |
| – Requires `OPENAI_API_KEY` server variable | – Requires Ollama running locally |
| – Data is sent to OpenAI servers | – Quality varies by model size (7B+ recommended) |

> [!NOTE]
> **`gpt-4o-mini` and `llama3.2` are hardcoded prose here**, and they match the backend's real defaults
> today. They will **not** track an environment override: a deployment that sets a different chat model
> keeps reading the old name in this copy. The live values are the ones in the model picker, which come
> from the API.

The footer of the selector summarises the active choice as `🦙 <model>` or `🤖 <model>`, degrading to
`🤖 ⚠ No key`, and adds a `⚠ offline` marker when Ollama is selected but unreachable.

---

## 📍 2. WHERE IT LIVES

Paths are relative to `Frontend/src/pages/configuration/`.

```text
pages/configuration/
│
├── 📁 views/
│   └── 📄 ConfigView.vue                  Layout + two static comparison cards + Quick Start. 138 lines
│
└── 📁 components/
    └── 📁 LLMSelector/
        └── 📄 LLMSelector.vue             Provider buttons, model pickers, refresh, poll. 204 lines
```

| Concern | Path | Anchor |
|---|---|---|
| Page layout | `views/ConfigView.vue:17` | `lg:grid-cols-[380px_1fr]` |
| Availability computeds | `views/ConfigView.vue:122-123` | `openaiAvailable`, `ollamaAvailable` |
| Quick Start block | `views/ConfigView.vue:94-106` | *(gated on `!ollamaAvailable`)* |
| Feature lists | `views/ConfigView.vue:125-137` | the two hardcoded arrays |
| Derived provider state | `components/LLMSelector/LLMSelector.vue:174-185` | `openaiInfo` … `activeOllamaModel` |
| Provider selection | `components/LLMSelector/LLMSelector.vue:187` | `select` |
| Manual refresh | `components/LLMSelector/LLMSelector.vue:193` | `refresh` |
| The poll | `components/LLMSelector/LLMSelector.vue:195-203` | `onMounted` / `onUnmounted` |

---

## 🏗️ 3. ARCHITECTURE

### 3.1 Two halves, one store

`ConfigView` is `lg:grid-cols-[380px_1fr]` (`:17`): a fixed-width column holding `<LLMSelector />`, and
a fluid column holding the two informational cards. It reads the store for exactly two computeds —
`openaiAvailable` (`:122`) and `ollamaAvailable` (`:123`), both defaulting to `false` with `?? false`.

`LLMSelector` has **no props and no emits** (`:169` is its only import of substance). It reads and
writes the store directly. That is unusual for this codebase, where components normally either take
props or call actions — and it is deliberate: everything this component owns is global selection state
that the chat page reads on the next query. Threading it through props would mean the page owning state
it does not use.

### 3.2 Derived state

Six computeds turn one store object into everything the template needs (`:174-185`):

| Computed | Line | Derivation |
|---|---|---|
| `openaiInfo` / `ollamaInfo` | `:174-175` | `store.availableProviders.<id>`, defaulting to `{ available: false }` |
| `openaiModels` / `ollamaModels` | `:176-177` | `.models ?? []` |
| `ollamaError` | `:178` | `.error ?? ''` — **see §7.1** |
| `activeOpenaiModel` | `:180-182` | `store.openaiModel \|\| openaiInfo.model \|\| openaiModels[0] \|\| null` |
| `activeOllamaModel` | `:183-185` | `store.ollamaModel \|\| ollamaModels[0] \|\| ollamaInfo.model \|\| null` |

Every one defaults rather than guards, so the first render — before any fetch has returned — produces a
complete, inert UI rather than a flash of missing data.

---

## 🔄 4. LIFECYCLE & STATE MACHINE

### 4.1 Mount and first fetch

`onMounted` (`:195-202`) calls `store.fetchProviders()` once, then starts the interval. The store's
fetch does three things in sequence: reshape the wire array into a map keyed by provider id, auto-select
a provider, and pre-fill the OpenAI model if none is chosen. The full cascade — including why a server
default naming an unavailable provider does not strand the UI — is in
[`../state/README.md`](../state/README.md).

`refresh()` (`:193`) is the manual version: set `checking`, `await store.fetchProviders()`, clear it. The
↻ glyph spins via `animate-spin` while `checking` is true (`:8`).

### 4.2 The polling loop

```js
// src/pages/configuration/components/LLMSelector/LLMSelector.vue:195
onMounted(async () => {
  await store.fetchProviders()
  timer = setInterval(async () => {
    if (!ollamaInfo.value.available) await store.fetchProviders()
  }, 15_000)
})
onUnmounted(() => clearInterval(timer))
```

**Precision matters here, because the obvious description is wrong.** The interval **always ticks** for
as long as the component is mounted; only the *fetch inside it* is conditional. It is not "polls while
offline and stops when online" — it is **"ticks every 15 seconds, re-checks only while Ollama is down,
and stops on unmount."** Once Ollama comes up, the timer keeps firing and does nothing.

> [!IMPORTANT]
> **Each tick that does fetch is a real backend round-trip that can block for seconds.**
> `GET /api/providers` probes the Ollama server over the network on **every** request — it is the only
> route in the whole API that makes an outbound call, and it is the only one with a meaningful
> worst-case latency. Leaving this page open with Ollama down means a probe every fifteen seconds, each
> one occupying a request thread on a single-worker server.
>
> This is the reason the fetch is conditional rather than the interval: the guard exists to stop the
> probe once it has nothing left to discover.

### 4.3 Choosing a provider

```js
// src/pages/configuration/components/LLMSelector/LLMSelector.vue:187
function select (p) {
  store.llmProvider = p
  if (p === 'ollama' && !store.ollamaModel && ollamaModels.value.length) {
    store.setOllamaModel(ollamaModels.value[0])
  } else if (p === 'openai' && !store.openaiModel && openaiInfo.value.model) {
    store.setOpenaiModel(openaiInfo.value.model)
  }
}
```

Two things to notice:

- **`store.llmProvider = p` is a direct write**, not an action call. It is legal in Pinia and it is the
  one place in the frontend where a component assigns store state rather than calling a function. The
  model setters below it *are* actions, which makes the asymmetry visible in the same six lines.
- **Selecting a provider auto-adopts a model** if none has been chosen — the first installed Ollama
  model, or the server's reported OpenAI model. Choosing a provider therefore never leaves the query
  without a model to send.

---

## ⚙️ 5. KEY ALGORITHMS & DATA STRUCTURES

### 5.1 The two fallback chains

`activeOpenaiModel` and `activeOllamaModel` look symmetric and are not:

| Provider | Order of preference |
|---|---|
| OpenAI | the user's choice → **the server-reported model** → the first of the list → `null` |
| Ollama | the user's choice → **the first installed model** → the server-reported model → `null` |

**The inversion is deliberate.** OpenAI's model list is a fixed set of names that the server knows are
valid, so the server's configured model is the better second choice. Ollama's list is *what is actually
pulled on this machine*, and the server's configured `OLLAMA_MODEL` may name a model that was never
downloaded — so preferring an installed model avoids selecting something that will fail at call time.

### 5.2 The model pickers

Both pickers are **button lists**, not dropdowns.

The **OpenAI** list (`:94-118`) renders only when
`llmProvider === 'openai' && openaiInfo.available && openaiModels.length`. Its four entries — `gpt-4o`,
`gpt-4o-mini`, `gpt-4-turbo`, `gpt-3.5-turbo` — are **hardcoded on the server**, not discovered from
OpenAI's API. Clicking one calls `store.setOpenaiModel(m)`.

The **Ollama** list (`:120-148`) renders when `llmProvider === 'ollama' && ollamaInfo.available`, with an
empty fallback reading *"No models found — run `ollama pull llama3.2`"* (`:145-147`). Its entries are
whatever the local server reports. Clicking one calls `store.setOllamaModel(m)`.

Each row shows a dot, the model name in `font-mono`, and an "active" pill on the current selection.

> [!NOTE]
> **The backend cannot distinguish "Ollama is up but could not list models" from "Ollama is up with zero
> models pulled."** Both arrive as `available: true, models: []`, which this UI renders as the "No models
> found" hint. That hint is right in the common case and misleading in the rare one.

### 5.3 The `model` field applies to both providers

When a query runs, the store sends the selected model for **either** provider, and the backend honours
it for both: `model` overrides the chat model whichever provider is active.

This is worth stating because two code comments say otherwise — the HTTP client's JSDoc calls it an
*"Ollama model override"*, and a comment in the backend's query route agrees. **Both are stale; the
behaviour is the contract.** The strongest corroboration is on this very page: `GET /api/providers`
ships a four-item OpenAI model list, and that list would be pointless if the field were ignored for
OpenAI.

---

## 🔌 6. WIRE SHAPE (CROSS-BOUNDARY CONTRACTS)

This page drives exactly one route: **`GET /api/providers`**, through `ragStore.fetchProviders()`.

The response is an array plus a default:

```json
{
  "providers": [
    { "id": "openai", "label": "OpenAI", "model": "gpt-4o-mini",
      "base_url": null, "available": true,
      "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"] },
    { "id": "ollama", "label": "Ollama", "model": "llama3.2",
      "base_url": "http://localhost:11434", "available": false, "models": [] }
  ],
  "default": "openai"
}
```

| Field | Used for |
|---|---|
| `id` | the map key the store builds, and every `availableProviders.<id>` read here |
| `label` | not read by this component — it renders its own headings |
| `model` | the server-configured chat model; second in OpenAI's chain, third in Ollama's |
| `base_url` | not read by this component |
| `available` | the status pills, the picker conditions, and the poll guard |
| `models` | the picker rows |
| `default` | the store's auto-selection, applied only if that provider is available |

**Six fields per provider, and `error` is not one of them** — which is the subject of §7.1.

> [!IMPORTANT]
> **`available` is a boolean and must stay one.** For OpenAI it means *the server holds an API key*, and
> the key itself never crosses the wire. That is the whole of the credential boundary: the browser learns
> whether a provider can be used and nothing about how. The full endpoint reference is
> [`../../../Backend/Documentation/api/provider-and-health.md`](../../../Backend/Documentation/api/provider-and-health.md).

The selections this page writes leave the frontend later, on the query request, as
`{ query, provider, model }` — see [`../api-clients/README.md`](../api-clients/README.md).

---

## ⚠️ 7. EDGE CASES & GOTCHAS

### 7.1 The "Cannot reach Ollama" panel can never render

> [!NOTE]
> **`LLMSelector.vue:80-91` is unreachable UI.** The red panel — with its heading, its explanation and
> its `ollama serve` / `ollama pull` instructions — is gated on
> `v-if="!ollamaInfo.available && ollamaError"`, and `ollamaError` is `ollamaInfo.value.error ?? ''`
> (`:178`).
>
> **`GET /api/providers` never sends an `error` key.** The route builds each provider entry from exactly
> six fields — `id`, `label`, `model`, `base_url`, `available`, `models` — and reads only `available` and
> `models` from its Ollama probe, discarding that probe's `warning` and `error` values. So `ollamaError`
> is permanently `''`, the second half of the condition is always false, and the panel is dead code.
>
> **Users are not stranded.** `ConfigView.vue:94-106` shows an equivalent Quick Start block on the same
> page, gated only on `!ollamaAvailable` — so the guidance the dead panel was written to give is
> delivered anyway, a few hundred pixels to the right. The *page* works; the *panel* does not.
>
> This is **pre-existing**, not a regression. Closing it is a small backend change — pass the probe's
> `error` through into the provider entry — or a small frontend one: delete the branch, since its content
> is duplicated. It is documented here rather than fixed because this is a documentation pass.

**The rest:**

- **The interval never stops while mounted** (§4.2). Only the fetch is conditional.

- **`select()` writes store state directly**, unlike every other component in the tree.

- **`gpt-4o-mini` and `llama3.2` appear as hardcoded prose** in the informational cards and the Quick
  Start block, and will not track an environment override.

- **The OpenAI model list is server-hardcoded**, not discovered — a model added by OpenAI will not
  appear here until the backend's list is edited.

- **`available: true, models: []` is ambiguous** — could be a listing failure, could be an empty
  install.

- **There is no persistence.** Provider and model selections live in the store only; a page reload
  re-runs `fetchProviders()` and re-applies the auto-selection cascade. The theme persists; this does
  not.

- **Selecting an unavailable provider is prevented by the buttons**, not by the store. Nothing in
  `ragStore` refuses `llmProvider = 'ollama'` when Ollama is down.

---

## 💥 8. FAILURE MODES

| Failure | What the user sees | Behaviour |
|---|---|---|
| Backend down | Both providers show unavailable; no error text | `fetchProviders` swallows its error by design |
| Ollama down | `✗ Offline`, the Quick Start block, and a probe every 15 s | The dead panel does **not** appear (§7.1) |
| No `OPENAI_API_KEY` on the server | `⚠ No key`, no model list, footer reads `🤖 ⚠ No key` | `available: false` from the server |
| Ollama up, no models pulled | *"No models found — run `ollama pull llama3.2`"* | `models: []` |
| Ollama slow to answer | The whole page's refresh stalls until the probe returns | The endpoint probes on every request |
| Both providers unavailable | The store leaves `llmProvider` at its last value | The auto-select cascade falls through untouched |
| The user navigates away mid-poll | The interval is cleared | `onUnmounted` |

---

## 🧩 9. EXTENSION POINTS

**Add a third provider.** Almost all the work is on the server: add its entry to the provider payload
with the same six fields, and teach the LLM factory to construct it. On this page, add a card following
the existing two — an `<info>` computed, a status pill, a picker gated on availability, and a branch in
`select()` for its model auto-adopt. The store needs no change beyond a per-provider model ref if the
new provider has its own model list.

**Make the dead panel live.** Either pass the probe's `error` through into the provider entry on the
server — at which point `LLMSelector.vue:80-91` starts rendering with no frontend change at all — or
delete the branch and rely on `ConfigView`'s Quick Start. Do not leave it as it is on the assumption it
works.

**Persist the selection.** Follow the theme's pattern in the `'ui'` store: a namespaced `localStorage`
key, a read at store creation, an explicit write in the setter. The auto-selection cascade would then
need to respect a stored choice ahead of the server default.

**Reduce the polling cost.** Back off the interval after repeated failures, or stop the timer entirely
once Ollama reports available rather than merely skipping the fetch. Both are changes to the same nine
lines.

**What not to touch.** Do not make `/api/providers` return the API key or any part of it — `available`
is a boolean and that is the credential boundary. Do not make the poll unconditional; each tick is an
outbound network probe on a single-worker server.

---

## 🔗 10. RELATED DECISIONS & DEEPER READING

- **Selection as store state, not a form.** No Save button, no draft, no dirty flag. The consequence is
  that a reload discards the choice — an acceptable trade for a selection that takes one click, and one
  that would become annoying if the choice ever grew to more than two fields.

- **Buttons instead of a dropdown.** With four models and no search need, a list shows every option and
  the active one at a glance, and it leaves room for a per-row status dot. A `<select>` would be shorter
  and would hide the thing the page exists to show.

- **Polling instead of a push.** The backend has an event stream, but it is scoped to a query run. A
  fifteen-second poll is the cheapest way to notice a local server starting, and gating the fetch on
  unavailability keeps the steady-state cost at zero requests.

- **Availability as a boolean.** The server could report *why* a provider is unavailable, and the dead
  panel in §7.1 is the fossil of an interface that intended to. Reporting only a boolean keeps the
  credential boundary trivially auditable — there is no field that could accidentally carry a key or a
  path.

**Continue reading:**

- [`../state/README.md`](../state/README.md) — `fetchProviders`, the auto-selection cascade, the model refs
- [`../api-clients/README.md`](../api-clients/README.md) — how `provider` and `model` reach the query request
- [`../chat/README.md`](../chat/README.md) — where the selection is actually used
- [`../../../Backend/Documentation/api/provider-and-health.md`](../../../Backend/Documentation/api/provider-and-health.md) — the endpoint in full
- [`../../../Backend/Documentation/llm-providers/README.md`](../../../Backend/Documentation/llm-providers/README.md) — the factory, the probe, and what "available" means on the server
