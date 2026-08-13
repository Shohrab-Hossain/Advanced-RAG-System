# 🏗️ Architecture

The static structure of adRAG: what the components are, what each is responsible for, and where the
boundaries sit. The *dynamic* side — how a query actually moves through these components — lives in
[`../runtime/`](../runtime/README.md).

<br>

---

<br>

## Index

| Doc | Holds |
|---|---|
| [`system-overview.md`](system-overview.md) | The two processes, the single HTTP boundary between them, and the end-to-end flows |
| [`backend.md`](backend.md) | The Flask app, the `rag_pipeline` package layout, the three stores, and the module dependency graph |
| [`frontend.md`](frontend.md) | The Vue 3 SPA — routes, stores, components, and how state flows through them |

<br>

---

<br>

## The shape in one screen

Two processes, one boundary:

```
Browser (Vue 3 SPA, :8080 dev)
        │  HTTP JSON  +  SSE stream
        ▼
Flask API (:5001 default)  ──►  LangGraph pipeline (in a background thread)
                            │
                            ├─► Chroma vector store   (embedded, on disk)
                            ├─► BM25 store            (pickle, in memory)
                            ├─► NetworkX graph store  (pickle, in memory)
                            ├─► LLM: OpenAI  |  Ollama (localhost:11434)
                            └─► DuckDuckGo web search  (optional)
```

Three properties define the architecture and explain most of the code:

1. **All state is process-global and single-corpus.** The three stores are singletons instantiated at
   import time; there is no per-user or per-document partitioning. Restarting the server reloads them from
   disk.
2. **The pipeline is a graph, not a chain.** `graph.py` compiles a `StateGraph` with a three-way
   conditional branch out of the planner and a backward edge from reflection to retrieval. A single
   `RAGState` dict is threaded through; each node returns only the keys it changes.
3. **Progress is pushed, not polled.** Nodes emit typed events into a per-session in-memory queue, and the
   Flask route drains that queue into a `text/event-stream` response while the pipeline runs in a daemon
   thread. This is why the server must run threaded and single-worker.
