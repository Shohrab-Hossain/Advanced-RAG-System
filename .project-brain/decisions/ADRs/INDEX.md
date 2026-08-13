# 📇 ADR Index

Every architecture decision on record, newest number last. Add a row in the same edit that adds an entry.

<br>

---

<br>

## Records

| # | Decision | Date | Status | One-line summary |
|---|---|---|---|---|
| [001](entries/001-langgraph-state-machine.md) | LangGraph state machine for the RAG pipeline | 2026-08-13 | accepted | The flow branches and loops, so it is a compiled `StateGraph`, not a call chain |
| [002](entries/002-three-store-hybrid-retrieval.md) | Three-store hybrid retrieval | 2026-08-13 | accepted | Vector + BM25 + entity graph queried per request, merged, then cross-encoder reranked |
| [003](entries/003-sse-for-pipeline-progress.md) | Server-Sent Events for pipeline progress | 2026-08-13 | accepted | One-way progress streaming over a POST body via a per-session in-memory queue |
| [004](entries/004-embedded-file-backed-stores.md) | Embedded, file-backed stores | 2026-08-13 | accepted | Chroma `PersistentClient` + two pickles instead of any database server |
| [005](entries/005-dual-llm-provider.md) | Dual LLM provider (OpenAI + Ollama) | 2026-08-13 | accepted | Provider chosen per request so the system can run fully local |
| [006](entries/006-dev-launcher-env-injected-ports.md) | Dev launcher owns both ports, injected as child env | 2026-08-13 | accepted | `dev.py` picks both ports before spawn and injects them — no file written, no port scraped |

<br>

---

<br>

> [!IMPORTANT]
> **These five records were reconstructed on 2026-08-13** from the code, not written at the time each
> decision was made. Their *Context*, *Decision*, and *Consequences* are grounded in what the repository
> actually contains; where the original reasoning or the alternatives weighed are not evidenced anywhere in
> the repository, the record says so explicitly with a `TODO:`. Confirm those with the project owner before
> treating them as recorded history. Every ADR written from here on should be captured **at the moment the
> decision is made**, which is the only way the *why* survives.
