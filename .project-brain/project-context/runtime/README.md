# ⚙️ Runtime

The dynamic behaviour of adRAG — the flows, lifecycles, and ordering rules you would otherwise have to
re-derive by reading the code, plus the gotchas that bite. The *static* structure lives in
[`../architecture/`](../architecture/README.md).

<br>

---

<br>

## Index

| Topic | Holds |
|---|---|
| [`backend-startup/`](backend-startup/README.md) | What happens between a start command and a serving process — the import-time sequence, the four traps that let it come up looking healthy while being wrong (working directory picks the corpus, `PORT` falls back to 5001, process env beats `.env`, the debug reloader), and what the `dev.py` launcher does about each |
| [`query-pipeline/`](query-pipeline/README.md) | The eight-node flow, the three-way planner branch, what each node reads and writes, and the reflection retry/escalation loop |
| [`sse-event-bus/`](sse-event-bus/README.md) | Session queues, the producer/consumer split across threads, the sentinel protocol, and the timeout behaviour |
| [`ingestion-indexing/`](ingestion-indexing/README.md) | Upload → hash → load → chunk → replace → index into three stores, and how persistence works per store |

<br>

---

<br>

## Cross-cutting runtime facts

- **Nothing survives a restart except what is on disk.** SSE sessions, the LLM cache, and the loaded models
  are process memory. The three store files and `kb_registry.json` are the durable state.
- **Model loading is lazy and first-run-expensive.** `SentenceTransformer` and `CrossEncoder` download from
  Hugging Face on first use; `main.py` deliberately silences those loggers and several warnings so the
  console stays readable.
- **No node ever raises.** Every node catches, emits a `stage_error` event, and returns a degraded but
  valid result. A failure shows up as a red row in the UI, not a 500.
- **A run is bounded by three numbers:** `RETRIEVAL_TOP_K` (10) candidates per store, `RERANK_TOP_K` (5)
  documents into the prompt, and `MAX_REFLECTION_RETRIES` (2) → at most 3 generation attempts. The SSE
  route additionally hard-stops at a 180-second queue timeout.
