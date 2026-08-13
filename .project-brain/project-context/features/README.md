# ✨ Features

One folder per feature — the convention here is **folder always**, even for a single-doc feature, so a
spec can grow sub-docs without any restructuring. Each spec names what the feature does, the exact files
that implement it, its inputs and outputs, what it depends on, and its gotchas.

<br>

---

<br>

## Catalog

| Feature | Does | Surfaces |
|---|---|---|
| [`self-rag-pipeline/`](self-rag-pipeline/README.md) | The core product: plan → retrieve → aggregate → rerank → compress → answer → verify, with a grounding retry loop | Backend only (drives every other feature) |
| [`hybrid-retrieval/`](hybrid-retrieval/README.md) | Three retrievers (dense vector, BM25, entity graph) queried per request and merged | Backend |
| [`knowledge-base-management/`](knowledge-base-management/README.md) | Upload, list, inspect, and delete documents; index statistics | Backend + `KnowledgeBaseView`, `UploadPanel`, `IndexStats`, `KnowledgeBaseList` (`knowledgeBase` store) |
| [`pipeline-tracker/`](pipeline-tracker/README.md) | Live stage-by-stage visualisation of a running query | Frontend `PipelineTracker` + `StageRow`, fed by the SSE stream |
| [`llm-provider-selection/`](llm-provider-selection/README.md) | Choose OpenAI or a local Ollama model at query time; availability probing | Backend `/api/providers` + `ConfigView`, `LLMSelector`, the `NavBar` badge |
| [`chat-history/`](chat-history/README.md) | Browser-local record of past queries, answers, sources, and stage snapshots | Frontend only — `ChatHistorySidebar` over `localStorage` |

<br>

---

<br>

## Dependency map

```
knowledge-base-management  ──feeds──►  hybrid-retrieval  ──feeds──►  self-rag-pipeline
                                                                          │
                                              llm-provider-selection ─────┤ (which model runs each node)
                                                                          │
                                                                     SSE events
                                                                          │
                                                          pipeline-tracker ├──► chat-history
                                                                          │     (snapshots the result
                                                                           )     + stage statuses)
```

- **`self-rag-pipeline`** is the hub: everything else either feeds it or renders it.
- **`hybrid-retrieval`** is empty until `knowledge-base-management` has indexed something; a query against
  an empty index still runs, producing zero context and a direct-answer fallback.
- **`pipeline-tracker`** and **`chat-history`** are pure consumers — removing either does not affect the
  backend.
- **`llm-provider-selection`** cross-cuts every LLM-calling node (planner, compressor, reasoning,
  reflection); the chosen provider and model are carried in `RAGState` for the whole run.

<br>

---

<br>

## Where these features live in the frontend

Each feature maps onto one owner in `Frontend/src/`, which is sorted by ownership rather than by kind:

| Feature | Owner |
|---|---|
| `knowledge-base-management` | `pages/knowledge-base/` (screen) + `subsystems/knowledge-base/` (state + HTTP) |
| `pipeline-tracker` · `chat-history` | `pages/chat/components/` — both read `subsystems/rag/` |
| `llm-provider-selection` | `pages/configuration/` — state lives on `subsystems/rag/ragStore.js`, because the provider rides the query itself |
| `self-rag-pipeline` · `hybrid-retrieval` | Backend only; the frontend sees them solely as the SSE stream |

> [!IMPORTANT]
> **Exactly two components read both subsystem stores** — this is the only cross-subsystem edge in the app,
> and both cases are deliberate. `ChatView.vue:118-119` pairs `ragStore` (query lifecycle) with `kbStore`
> (`hasDocuments`, for the "no documents indexed" warning at `:41`), and `NavBar.vue:108-111` pairs
> `ragStore` (provider/model badge) with `kbStore` (`refreshStats` + `fetchKnowledgeBases` on mount,
> `:144`) plus the `ui` store and `ragApi`. `NavBar.vue:111`'s `healthCheck` import is the one accepted
> exception to *components call store actions, not the service* — it survived the reorganisation intact.
> The subsystems themselves **never import each other**.
