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
| [`knowledge-base-management/`](knowledge-base-management/README.md) | Upload, list, inspect, and delete documents; index statistics | Backend + `KnowledgeBaseView`, `FileUpload`, `KnowledgeBases` |
| [`pipeline-tracker/`](pipeline-tracker/README.md) | Live stage-by-stage visualisation of a running query | Frontend, fed by the SSE stream |
| [`llm-provider-selection/`](llm-provider-selection/README.md) | Choose OpenAI or a local Ollama model at query time; availability probing | Backend `/api/providers` + `ConfigView`, `LLMSelector` |
| [`chat-history/`](chat-history/README.md) | Browser-local record of past queries, answers, sources, and stage snapshots | Frontend only (`localStorage`) |

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
