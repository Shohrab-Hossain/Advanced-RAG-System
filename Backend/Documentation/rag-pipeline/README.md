<div align="center">

# 🧬 RAG Pipeline

### The eight-node LangGraph state machine that turns one question into one cited, grounding-verified answer.

<br>

[![LangGraph](https://img.shields.io/badge/LangGraph-state%20machine-1c7ed6)](https://langchain-ai.github.io/langgraph/)
[![Nodes](https://img.shields.io/badge/nodes-8-7c5cff)](#%EF%B8%8F-3-architecture)
[![Version](https://img.shields.io/badge/version-0.1.0-3fb950)](../../pyproject.toml)

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776ab?logo=python&logoColor=white)](https://www.python.org/)
[![Transport](https://img.shields.io/badge/progress-SSE-f59e0b)](#-6-wire-shape-cross-boundary-contracts)

</div>

<br>

---

<br>

## Content Tree

<pre>
RAG Pipeline
│
├── <a href="#-overview">📖 Overview</a>
│
├── <a href="#-1-purpose--user-visible-behavior">🎯 1. Purpose &amp; user-visible behavior</a>
│   ├── <a href="#11-what-the-user-does">1.1 What the user does</a>
│   ├── <a href="#12-what-the-user-sees">1.2 What the user sees</a>
│   └── <a href="#13-the-three-shapes-a-run-can-take">1.3 The three shapes a run can take</a>
│
├── <a href="#-2-where-it-lives">📍 2. Where it lives</a>
│   ├── <a href="#21-the-file-map">2.1 The file map</a>
│   └── <a href="#22-the-package-tree">2.2 The package tree</a>
│
├── <a href="#%EF%B8%8F-3-architecture">🏗️ 3. Architecture</a>
│   ├── <a href="#31-the-eight-nodes-and-the-graph-that-wires-them">3.1 The eight nodes and the graph that wires them</a>
│   ├── <a href="#32-the-two-conditional-edges">3.2 The two conditional edges</a>
│   ├── <a href="#33-the-node-contract">3.3 The node contract</a>
│   └── <a href="#34-what-the-pipeline-deliberately-does-not-know">3.4 What the pipeline deliberately does not know</a>
│
├── <a href="#-4-lifecycle--state-machine">🔄 4. Lifecycle &amp; state machine</a>
│   ├── <a href="#41-one-pass-end-to-end">4.1 One pass, end to end</a>
│   ├── <a href="#42-the-reflection-retry-state-machine">4.2 The reflection retry state machine</a>
│   ├── <a href="#43-the-retry-budget-and-where-it-actually-lives">4.3 The retry budget, and where it actually lives</a>
│   └── <a href="#44-termination">4.4 Termination</a>
│
├── <a href="#%EF%B8%8F-5-key-algorithms--data-structures">⚙️ 5. Key algorithms &amp; data structures</a>
│   ├── <a href="#51-the-self-rag-planner-decision">5.1 The Self-RAG planner decision</a>
│   ├── <a href="#52-the-citation-index-chain">5.2 The citation-index chain</a>
│   ├── <a href="#53-the-grounding-critic">5.3 The grounding critic</a>
│   ├── <a href="#54-the-web-search-escalation-heuristic">5.4 The web-search escalation heuristic</a>
│   └── <a href="#55-json-discipline-across-two-very-different-models">5.5 JSON discipline across two very different models</a>
│
├── <a href="#-6-wire-shape-cross-boundary-contracts">🔌 6. Wire shape (cross-boundary contracts)</a>
│   ├── <a href="#61-the-seven-pipeline-event-types">6.1 The seven pipeline event types</a>
│   ├── <a href="#62-the-stage-id-contract">6.2 The stage-id contract</a>
│   └── <a href="#63-events-the-route-frames-not-the-pipeline">6.3 Events the route frames, not the pipeline</a>
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

The RAG pipeline is a **LangGraph state machine of eight nodes** that takes a user's question and
produces an answer with inline `[1]`, `[2]` citations, a grounding verdict, and a live progress stream.
It plans whether to retrieve at all, fans out across three local stores plus an optional web search,
merges and reranks the evidence, compresses it if it is too long, generates a cited answer, and then
runs a **second LLM as a critic** that decides whether the answer is actually supported — and, if not,
whether to try again.

Everything the nodes share travels in one `TypedDict`, `RAGState`
([`state.py`](../../src/adrag/custom_packages/rag_pipeline/state.py)). Everything the browser sees
travels out of band, as Server-Sent Events pushed by `emit()`.

> [!IMPORTANT]
> **`final_answer` is the termination signal, and it is the *only* one.** The reflection router
> (`_route_reflection`, `workflow.py:47`) tests `state.get("final_answer")` for truthiness and nothing
> else — not `grounded`, not `retry_count`, not the retry budget. Any node that writes a non-empty
> `final_answer` ends the graph; any path that reaches `reflect` without one loops back to `retrieval`.
> The retry budget is enforced *inside* the reflection node (`reflection.py:97`), not by the router.

**The three companion pages in this folder:**

| Page | What it covers |
|---|---|
| [`nodes.md`](nodes.md) | Per-node reference — all eight, with reads, returns, prompts, emits and failure paths |
| [`state-model.md`](state-model.md) | `RAGState` key by key, LangGraph merge semantics, and the invariants that follow |
| [`../hybrid-retrieval/README.md`](../hybrid-retrieval/README.md) | The three-store retrieval subsystem the `retrieval` node drives |

---

## 🎯 1. PURPOSE & USER-VISIBLE BEHAVIOR

### 1.1 What the user does

The user types a question in the chat page and picks a provider (`openai` or `ollama`). The browser
`POST`s to `/api/query` and immediately begins reading a `text/event-stream` response. Nothing else is
required — there is no polling, no job id, no second request.

### 1.2 What the user sees

An eight-row pipeline tracker updates live as the run progresses. Each row is driven by SSE events
carrying a `stage` id; a row moves through **idle → active → complete**, or lands on **skipped** or
**error**. Alongside the rows, the tracker shows the concrete numbers each stage reports:

| Stage row | What it shows while running |
|---|---|
| `planner` | the retrieve / web-search decision, the query type, and the model's one-sentence reasoning |
| `retrieval` | per-store hit counts — `Vector: 10 \| BM25: 7 \| Graph: 3` |
| `external_tools` | the web result count, or `Web search not needed` when skipped |
| `aggregator` | `N unique docs (from M total, M−N duplicates removed)` |
| `reranker` | the rounded cross-encoder scores of the selected top-k, and their source stores |
| `compressor` | `original_chars → compressed_chars`, or `Context already within limit` |
| `reasoning` | the model's self-reported confidence |
| `reflection` | `✓ Grounded` / `✗ Not grounded`, confidence, and whether a retry is coming |

When the run ends, a `done` event delivers the answer, the cited sources, and the run metadata. The
answer is rendered as Markdown; each source becomes an expandable card carrying its file name, page,
rerank score, a 250-character preview, and the full chunk text.

### 1.3 The three shapes a run can take

The planner decides the shape before any retrieval happens, so the same endpoint serves three quite
different behaviours:

1. **Document question** — `retrieve=true`. All three local stores are searched, the evidence is
   reranked to five documents, and the answer cites them.
2. **Live-data question** — `retrieve=false, use_external=true`. The knowledge base is bypassed
   entirely and DuckDuckGo results become the only evidence.
3. **Direct answer** — `retrieve=false, use_external=false`. Both retrieval nodes are bypassed, the
   context is empty, and the reasoning node falls through to a plain, uncited LLM call. Greetings,
   arithmetic and coding questions land here by design.

---

## 📍 2. WHERE IT LIVES

### 2.1 The file map

Paths are relative to the package root, `Backend/src/adrag/`.

| Concern | Path | Anchor |
|---|---|---|
| Graph builder + routers | `custom_packages/rag_pipeline/workflow.py` | `build_graph`, `_route_planner`, `_route_reflection` |
| Compiled singleton | `custom_packages/rag_pipeline/workflow.py:107` | `rag_graph = build_graph()` |
| Shared state | `custom_packages/rag_pipeline/state.py` | `RAGState`, `Document` |
| Event bus | `custom_packages/rag_pipeline/events.py` | `emit`, `create_session`, `format_sse` |
| HTTP entry point | `routes/query/query_routes.py:33` | `query()` — `POST /api/query` |
| LLM factory | `custom_packages/rag_pipeline/models/llm.py:24` | `get_llm`, `safe_json_parse` |

The route imports exactly one thing from the pipeline —
`from adrag.custom_packages.rag_pipeline.workflow import rag_graph` (`query_routes.py:17`) — plus the
three session helpers. That single import is the whole coupling between HTTP and the graph.

### 2.2 The package tree

```text
custom_packages/rag_pipeline/
│
├── 📁 generation/           The four LLM nodes
│   ├── 📄 planner.py         Self-RAG decision — retrieve? web? query type?
│   ├── 📄 compressor.py      Conditional context compression
│   ├── 📄 reasoning.py       Cited answer generation
│   └── 📄 reflection.py      Grounding critic, loop controller, terminator
│
├── 📁 ranking/              Evidence shaping
│   ├── 📄 aggregator.py      Merge four lists, dedup by content hash
│   └── 📄 reranker.py        Cross-encoder scoring → top-k context
│
├── 📁 retrieval/            Evidence gathering
│   ├── 📄 hybrid_node.py     Fans out across the three local stores
│   ├── 📄 web_node.py        DuckDuckGo search (optional)
│   └── 📁 stores/            vector_store · bm25_store · graph_store
│
├── 📁 ingestion/            Write path — loader + KB registry
├── 📁 models/               LLM factory + embedding singleton
│
├── 📄 events.py             SSE event bus — session queues, emit()
├── 📄 state.py              RAGState TypedDict — the shared contract
└── 📄 workflow.py           Graph wiring + the two routers + rag_graph
```

---

## 🏗️ 3. ARCHITECTURE

### 3.1 The eight nodes and the graph that wires them

<p align="center">
  <img src="../../../.readme-lib/readme/diagrams/svg/rag-pipeline-flow.svg" alt="The eight-node RAG pipeline: planner branches three ways to retrieval, external_tools, or aggregate; retrieval flows to external_tools to aggregate; then the linear chain aggregate to rerank to compress to reason to reflect; reflect either loops back to retrieval or ends the run." width="760">
</p>

<sub>Diagram source: <a href="../../../.readme-lib/readme/diagrams/mermaid-source/rag-pipeline-flow.mmd"><code>rag-pipeline-flow.mmd</code></a> — edit it, then regenerate the SVG (don't hand-edit the SVG).</sub>

The eight `add_node` registrations, in the order `build_graph()` declares them:

| # | Node name | Bound function | Defined in | One-line responsibility |
|---|---|---|---|---|
| 1 | `planner` | `planner_node` | `generation/planner.py:49` | Decide whether to retrieve, whether to search the web, and the query type |
| 2 | `retrieval` | `retrieval_node` | `retrieval/hybrid_node.py:25` | Search the three local stores and return three separate result lists |
| 3 | `external_tools` | `external_tools_node` | `retrieval/web_node.py:20` | Search DuckDuckGo, or skip itself |
| 4 | `aggregate` | `aggregator_node` | `ranking/aggregator.py:19` | Concatenate the four lists and deduplicate by content hash |
| 5 | `rerank` | `reranker_node` | `ranking/reranker.py:34` | Score every candidate with a cross-encoder, keep the top five |
| 6 | `compress` | `compressor_node` | `generation/compressor.py:37` | Build the numbered context block; compress it only if it is too long |
| 7 | `reason` | `reasoning_node` | `generation/reasoning.py:43` | Generate the answer with inline citations and filter the source list |
| 8 | `reflect` | `reflection_node` | `generation/reflection.py:53` | Verify grounding, then either retry or finalize |

The entry point is `planner` (`builder.set_entry_point("planner")`, `workflow.py:72`). Every full node
reference — reads, returns, prompt, emits, failure paths — is in [`nodes.md`](nodes.md).

**Edges.** Six are static and two are conditional:

| Kind | Edge | Line |
|---|---|---|
| conditional | `planner` → `_route_planner` → {`retrieval`, `external_tools`, `aggregate`} | `workflow.py:75-83` |
| static | `retrieval` → `external_tools` | `workflow.py:87` |
| static | `external_tools` → `aggregate` | `workflow.py:88` |
| static | `aggregate` → `rerank` | `workflow.py:91` |
| static | `rerank` → `compress` | `workflow.py:92` |
| static | `compress` → `reason` | `workflow.py:93` |
| static | `reason` → `reflect` | `workflow.py:94` |
| conditional | `reflect` → `_route_reflection` → {`retrieval`, `END`} | `workflow.py:97-101` |

**There is exactly one loop edge in the entire graph: `reflect` → `retrieval`.** Nothing else cycles.

### 3.2 The two conditional edges

Both routers are pure functions of the state — they read keys and return a node name. Neither calls an
LLM, neither emits an event, and neither has side effects.

**The planner router** decides where the run *enters* the pipeline:

```python
# custom_packages/rag_pipeline/workflow.py:38
def _route_planner(state: RAGState) -> str:
    """After planner: decide entry point into the pipeline."""
    if state.get("retrieve", True):
        return "retrieval"
    if state.get("use_external", False):
        return "external_tools"
    return "aggregate"    # direct answer: skip all retrieval
```

**The reflection router** decides whether the run is over:

```python
# custom_packages/rag_pipeline/workflow.py:47
def _route_reflection(state: RAGState) -> str:
    """After reflection: loop back or finish."""
    # final_answer being set signals the reflection node chose to finalize
    if state.get("final_answer"):
        return END
    # Retry: go back to retrieval with incremented retry_count
    return "retrieval"
```

The route seeds `"final_answer": ""` before invoking the graph (`query_routes.py:76`). An empty string
is falsy, so the first arrival at `reflect` always evaluates the retry branch — the decision to end is
made by the node writing a non-empty `final_answer`, never by the router noticing the run is done.

### 3.3 The node contract

All eight nodes share one shape, and matching it is the whole of what "adding a node" means:

```python
def <name>_node(state: RAGState) -> dict:
    session_id = state.get("session_id")
    ...
    emit(session_id, "stage_start", {"stage": "<stage-id>", "message": "..."})
    ...
    return {"<only>": ..., "<the>": ..., "<keys>": ..., "<it>": ..., "<changed>": ...}
```

Three rules follow from it, and all three are load-bearing:

- **A node returns only the keys it modifies.** LangGraph merges the returned dict into the state.
- **Returned keys overwrite; they never accumulate.** `RAGState` declares no reducer on any field, so a
  retry's fresh `vector_docs` *replaces* the previous pass's rather than adding to it
  ([`state-model.md`](state-model.md) §3).
- **Progress is a side channel.** A node reports itself by calling `emit()`, never by returning
  something the route inspects. Nodes do not import Flask and know nothing about HTTP.

### 3.4 What the pipeline deliberately does not know

The layering here is one-directional and worth stating explicitly, because breaking it is easy and the
breakage is not immediately visible:

- **`rag_pipeline/` never imports `app.py`.** The dependency runs route → pipeline, never back.
- **Nodes never touch Flask.** A node receives `RAGState` and calls `emit()`. HTTP framing — the
  `text/event-stream` mimetype, the `data:` frames, the keep-alive headers — is the route's job
  (`query_routes.py:115-123`).
- **Stores never import nodes.** The three stores expose search/write methods and hold no pipeline
  knowledge.
- **Errors are in-band.** A pipeline exception becomes a **`200`** carrying an `error` event
  (`query_routes.py:92-96`), never an HTTP error status — by the time a node can fail, the response
  headers have already been sent.

---

## 🔄 4. LIFECYCLE & STATE MACHINE

### 4.1 One pass, end to end

A request produces a session, a queue, and a daemon thread; the response generator drains the queue
while the graph runs.

1. **`query()` validates the body** — a missing or empty `query` field is a `400`; a `provider` that is
   neither `openai` nor `ollama` is a `400` (`query_routes.py:41-46`). These are the only two HTTP
   error statuses the endpoint can return.
2. **A session is created** — `session_id = str(uuid.uuid4())` and `create_session(session_id)` returns
   the queue that `emit()` will push into (`query_routes.py:51-52`).
3. **All 22 state keys are seeded** (`query_routes.py:54-79`). No key first appears mid-run; the
   planner's three outputs are seeded to `True`/`False`/`"factual"` under the comment *"Planner will
   overwrite these"*.
4. **A daemon thread calls `rag_graph.invoke(initial_state)`** (`query_routes.py:81-100`). The eight
   nodes run in-process on that thread, emitting as they go.
5. **The generator yields frames** — `event_queue.get(timeout=180)` in a loop, each item serialized by
   `format_sse` as `data: {json}\n\n` (`query_routes.py:102-111`).
6. **The run ends** — the thread pushes a `done` event with `{answer, sources, metadata}`, then a
   `None` sentinel; the generator yields `stream_end` and `close_session` pops the queue in a `finally`.

**Four LLM calls per pass**, all at `temperature=0`, all through `get_llm()`, all on the provider pinned
in `RAGState` for the whole run: planner, compressor (only when the context is over the limit),
reasoning, and reflection. There is no per-node model routing — the same model plans, compresses,
generates, and criticises.

### 4.2 The reflection retry state machine

<p align="center">
  <img src="../../../.readme-lib/documentation/rag-pipeline/diagrams/svg/reflection-retry-state-machine.svg" alt="The reflection retry state machine: reason drafts an answer and hands it to reflect, which owns the retry budget. Three transitions finalize by setting final_answer — grounded, no retry left with a caveat appended, and an exception that fails open. Three transitions leave final_answer unset — a plain retry incrementing retry_count, an escalation that also sets use_external, and an empty answer that spends no budget at all. Both outcomes reach _route_reflection, which tests final_answer only: set ends the run, unset loops back to retrieval for pass 2 or pass 3." width="760">
</p>

<sub>Diagram source: <a href="../../../.readme-lib/documentation/rag-pipeline/diagrams/mermaid-source/reflection-retry-state-machine.mmd"><code>reflection-retry-state-machine.mmd</code></a> — edit it, then regenerate the SVG (don't hand-edit the SVG).</sub>

The `reflect` node is simultaneously the critic, the loop controller, and the terminator. Every exit
from it is one of the seven transitions below, and the guards are exact:

| # | Guard | Goes to | Evidence |
|---|---|---|---|
| 1 | `answer` is empty → early return, **no `final_answer`, `retry_count` not incremented** | `retrieval` | `reflection.py:69-74` |
| 2 | `grounded` → finalize, `final_answer = answer` | `END` | `reflection.py:148`, `:160` |
| 3 | `¬grounded ∧ ¬should_retry` → finalize **with the caveat appended** | `END` | `reflection.py:144-148` |
| 4 | `¬grounded ∧ should_retry ∧ retry_count ≥ MAX_RETRIES` → budget spent, finalize with caveat | `END` | `reflection.py:97` false → `:143` |
| 5 | `¬grounded ∧ should_retry ∧ retry_count < MAX_RETRIES` ∧ ¬`kb_insufficient` → plain retry, `retry_count + 1` | `retrieval` | `reflection.py:97`, `:139` |
| 6 | same as 5 **∧ `kb_insufficient` ∧ ¬`use_external`** → escalate: also sets `use_external = True` | `retrieval`, web on | `reflection.py:102-104`, `:140` |
| 7 | any exception → `grounded = True`, `final_answer = answer` (**fails open**) | `END` | `reflection.py:172-181` |

The caveat in transitions 3 and 4 is appended verbatim to the answer text:

```python
# custom_packages/rag_pipeline/generation/reflection.py:144
caveat = (
    "\n\n⚠️ *Some claims may not be fully supported by the retrieved documents.*"
    if not grounded else ""
)
final_answer = answer + caveat
```

### 4.3 The retry budget, and where it actually lives

Three conditions must all hold for a retry to happen, and they are evaluated in one line:

```python
# custom_packages/rag_pipeline/generation/reflection.py:97
will_retry = (not grounded) and raw_retry and (retry_count < MAX_RETRIES)
```

- **`not grounded`** — the critic judged the answer unsupported.
- **`raw_retry`** — the critic *also* set `should_retry` in its JSON. **The model gets a veto:** it can
  call an answer ungrounded and still decline the retry, in which case the run finalizes with the
  caveat.
- **`retry_count < MAX_RETRIES`** — the budget. `MAX_REFLECTION_RETRIES` defaults to `2`.

`retry_count` starts at `0` and increments **only** on the retry branch (`reflection.py:139`), so the
maximum number of passes through `reason`/`reflect` is `MAX_RETRIES + 1` = **three** by default. The
node states that arithmetic itself, in the `attempt` / `max_attempts` pair it emits
(`reflection.py:65-66`).

> [!WARNING]
> **`workflow.py:33` defines `MAX_RETRIES` and never uses it — it is dead code.**
> `MAX_RETRIES = int(os.getenv("MAX_REFLECTION_RETRIES", "2"))` sits at module scope in `workflow.py`
> and is referenced nowhere in that file; the routers contain no budget logic at all. The constant that
> actually bounds the loop is the identically-named one at `reflection.py:21`, read at
> `reflection.py:97`. Both are fed by the same environment variable, so tuning
> `MAX_REFLECTION_RETRIES` does work — but **editing the literal default in `workflow.py` changes
> nothing observable**, and a reader who tunes it will see no behaviour change and reasonably conclude
> the retry loop is broken.

### 4.4 Termination

A run ends when `reflect` writes a non-empty `final_answer` and the router returns `END`. There are
exactly three writers of that key, all in `reflection.py`: the finalize path (`:160`), the exception
path (`:178`), and — indirectly — nothing else. That is what makes the invariant *only the node that
ends the run may write `final_answer`* enforceable by inspection rather than by a runtime check.

The route then reads the terminal state defensively:

```python
# routes/query/query_routes.py:87
"answer": result.get("final_answer") or result.get("answer", ""),
"sources": result.get("final_sources") or result.get("sources", []),
```

So even an abnormal termination that never reached the finalize path still delivers the raw answer to
the browser.

---

## ⚙️ 5. KEY ALGORITHMS & DATA STRUCTURES

### 5.1 The Self-RAG planner decision

**The problem:** running full hybrid retrieval on *"hi"* or *"what is 12 × 7"* costs three store
searches, a cross-encoder pass over thirty candidates, and two extra LLM calls — for evidence that will
be irrelevant. Worse, a low-quality retrieved chunk can actively degrade an answer the model already
knows. So the pipeline asks a cheap question first: **should we retrieve at all?**

The planner is one LLM call returning a four-field JSON object — `retrieve`, `use_external`,
`query_type`, and a one-sentence `reasoning`. The prompt carries explicit rules for both booleans plus
four worked examples (`planner.py:30-34`), which is what makes a small local model answer it usably.
Both booleans are coerced with defaults (`planner.py:65-66`), and a total failure returns
`{"retrieve": True, "use_external": False, "query_type": "factual"}` — **the planner fails toward
retrieval**, so an LLM outage degrades to a plain RAG query rather than to an uncited direct answer.

The routing truth table is where the subtlety is. `_route_planner` reads `retrieve` first, and that
first branch **swallows `use_external`**:

| `retrieve` | `use_external` | Router returns | What actually happens |
|---|---|---|---|
| `True` | `True` | `retrieval` | Web search **still runs** — `external_tools` is downstream of `retrieval` on a static edge |
| `True` | `False` | `retrieval` | `external_tools` runs but skips itself, emitting `stage_skip` |
| `False` | `True` | `external_tools` | The knowledge base is bypassed; the three KB lists stay `[]` |
| `False` | `False` | `aggregate` | Both retrieval nodes bypassed; `all_docs` is `[]` → the direct-answer path |

> [!IMPORTANT]
> **`use_external=True` does not route to `external_tools` unless `retrieve` is `False`.** On the
> `retrieve=True` path the planner's `use_external` is consumed by the *node* — `external_tools`
> decides for itself whether to run (`web_node.py:24`) — not by the *router*. This is why the graph can
> get away with one static `retrieval → external_tools` edge instead of a second conditional, and why
> "web search didn't run" is never explained by the router.

### 5.2 The citation-index chain

**The problem:** the model must cite sources by number, and those numbers must line up with the source
cards the UI renders. Nothing enforces that alignment at runtime — it holds because two nodes iterate
the same list in the same order.

The compressor builds the numbered context block, and that is where the indices are born:

```python
# custom_packages/rag_pipeline/generation/compressor.py:56
doc_blocks = []
for i, doc in enumerate(context):
    meta = doc.get("metadata", {})
    label = meta.get("file_name") or meta.get("title") or doc.get("source", f"Source {i+1}")
    doc_blocks.append(f"[{i+1}] {label}\n{doc['content']}")
full_text = "\n\n---\n\n".join(doc_blocks)
```

The reasoning node then builds its `sources` list from the **same `context` list, in the same order**,
assigning `"index": i + 1` (`reasoning.py:57-69`). The model sees `[1]`, `[2]`, … in the prompt, cites
those numbers in its answer, and returns them in `cited_sources`. The node uses that array to filter:

```python
# custom_packages/rag_pipeline/generation/reasoning.py:93
# Filter to only sources actually cited in the answer.
# If the LLM cited nothing (answered from training knowledge), return no sources.
cited_indices = set(result.get("cited_sources", []))
cited_sources = [s for s in sources if s["index"] in cited_indices]
```

Two consequences a reader will otherwise rediscover the hard way. **A retrieved-but-uncited document is
invisible in the UI** — that is deliberate, and it is why the source list is short. And **a model that
omits `cited_sources` from its JSON produces an answer with zero sources even though retrieval
succeeded** — the set is empty, so the filter keeps nothing. That is the mechanism behind "the answer
has no sources at all" reports, and it is a generation defect, not a retrieval one.

When compression is skipped (the common case — see §7), the reasoning node still receives the same
numbered `full_text`, because the compressor returns it verbatim. The indices survive either way.

### 5.3 The grounding critic

**The problem:** an LLM handed retrieved context will still assert things the context does not support,
and it will do so fluently. So a second LLM call reads the query, the context, and the answer, and
returns a verdict.

The prompt (`_REFLECTION_PROMPT`, `reflection.py:23-50`) names three criteria — every factual claim
traceable to the context, no hallucinated numbers/names/events, and citations that actually support
their claim — and closes with an explicit bias: *"Be strict: if ANY claim cannot be verified from the
context, set grounded=false."* It returns `grounded`, `confidence`, `issues`, `feedback`, and
`should_retry`.

Two details shape how it behaves in practice:

- **The defaults are optimistic.** `grounded` defaults to `True` and `confidence` to `0.8` when absent
  from the model's JSON (`reflection.py:90-91`). A response that parses but omits the verdict reads as
  *grounded*.
- **The critic sees a hard-truncated context.** `context_text[:4000]` (`reflection.py:85`) — a
  **hardcoded literal that is unrelated to `MAX_CONTEXT_CHARS`** despite sharing its default value.
  Raising `MAX_CONTEXT_CHARS` does not widen the critic's window; it only widens the generator's.

### 5.4 The web-search escalation heuristic

**The problem:** when the knowledge base genuinely has nothing relevant, retrying the identical search
is pointless. The pipeline needs to detect *"the KB had nothing useful"* and change strategy rather
than repeat itself.

```python
# custom_packages/rag_pipeline/generation/reflection.py:99
# Detect weak KB context: no docs or all cross-encoder scores below 0
# (ms-marco cross-encoder returns negative logits for irrelevant pairs)
max_rerank = max((d.get("rerank_score", 0) for d in context_docs), default=None)
kb_insufficient = len(context_docs) == 0 or (max_rerank is not None and max_rerank < 0)
# Escalate to web search on first retry when KB had nothing useful
escalate_external = will_retry and kb_insufficient and not state.get("use_external", False)
```

When it fires, the retry return merges one extra key in:

```python
# custom_packages/rag_pipeline/generation/reflection.py:136
return {
    "grounded": grounded,
    "reflection_feedback": feedback,
    "retry_count": retry_count + 1,
    **({"use_external": True} if escalate_external else {}),
}
```

That dict-unpacking conditional is **the only place outside the planner that writes `use_external`**,
and the only cross-node state mutation in the pipeline — one node reaching forward to change another
node's behaviour on the next pass.

> [!WARNING]
> **The *sign* of `rerank_score` is load-bearing.** The default cross-encoder
> `cross-encoder/ms-marco-MiniLM-L-6-v2` emits **raw unnormalised logits**, not probabilities —
> negative values are normal and mean "irrelevant." Swap `RERANKER_MODEL` for a model whose scores are
> non-negative (a sigmoid-output or normalised reranker) and `kb_insufficient` becomes permanently
> `False` for any non-empty context, **silently disabling escalation with no error anywhere.** Never
> describe `rerank_score` as a 0–1 relevance probability; that single misreading invalidates this whole
> mechanism.

### 5.5 JSON discipline across two very different models

Three of the four LLM calls need structured output, and the pipeline must work on both `gpt-4o-mini`
and a small local `llama3.2`. The strategy is deliberately belt-and-braces:

1. **Every structured prompt says so in words** — *"Respond ONLY with valid JSON — no markdown, no
   extra text"* — and includes the literal shape inline.
2. **`json_mode` is asymmetric by provider.** Ollama gets `format="json"` passed to the constructor
   (`llm.py:47-48`), a hard grammar constraint. **OpenAI gets nothing** — no `response_format`, no
   `.with_structured_output()`. For OpenAI, JSON discipline rests entirely on the prompt plus the
   salvage parser.
3. **`safe_json_parse` salvages what it can** (`llm.py:70-99`) — three escalating attempts: a direct
   `json.loads`; stripping a ` ```json ` fence; then extracting the first `{…}` block by regex. It
   raises `ValueError` with a 300-character excerpt if all three fail, which is exactly what each
   node's `except Exception` catches.

> [!NOTE]
> The reasoning node's own docstring says *"Output is a JSON object parsed by JsonOutputParser"*
> (`reasoning.py:7`). **No node uses a `JsonOutputParser`** — `safe_json_parse` does all parsing in this
> pipeline. The docstring is stale; the code is the contract.

---

## 🔌 6. WIRE SHAPE (CROSS-BOUNDARY CONTRACTS)

The pipeline crosses exactly one process boundary: it pushes progress events to the browser. It does so
indirectly, through an in-process queue that the HTTP route drains.

| Direction | Channel | Shape | Triggered by |
|---|---|---|---|
| Node → queue | in-process | `emit(session_id, event_type, data)` → `{"type": …, "data": {…}}` | every stage transition |
| Route → browser | SSE | `data: {"type": …, "data": {…}}\n\n` | the generator draining the queue |
| Browser → route | HTTP | `POST /api/query` with `{query, provider, model?}` | the user submitting a question |

`emit()` is a **no-op for an unknown session** — `if not session_id: return`, then `if q:`
(`events.py:31-37`). That is deliberate: a disconnected browser must not turn into a pipeline crash.

### 6.1 The seven pipeline event types

Thirty `emit()` call sites across the eight nodes produce **seven distinct event types**:

| Event type | Emitted by | Payload keys beyond `stage` | Meaning |
|---|---|---|---|
| `stage_start` | all eight nodes | `message` (+ `attempt`, `max_attempts` from `reflection`) | the stage began |
| `stage_complete` | six nodes | stage-specific stats | the stage finished normally |
| `stage_skip` | `retrieval`, `external_tools` | `message` | the stage declined to run |
| `stage_error` | six nodes | `error` | the stage caught an exception and degraded |
| `retrieval_result` | `hybrid_node` only | `vector_count`, `bm25_count`, `graph_count`, `message` | the three stores returned |
| `retry` | `reflection` only | `attempt`, `max_attempts`, `reason`, `escalate_external`, `message` | a retry is starting |
| `finalize` | `reflection` only | `grounded`, `message` | the terminating pass |

Two of these break the pattern, and both matter to anyone building a client:

> [!IMPORTANT]
> **`retrieval_result` is a `stage_complete` in disguise.** The hybrid retrieval node emits
> `retrieval_result` and **never** `stage_complete` (`hybrid_node.py:45`). A client that handles only
> the four `stage_*` types will leave the retrieval row stuck on *active* forever. The frontend handles
> this by falling through: `case 'stage_complete': case 'retrieval_result':`.

> [!IMPORTANT]
> **`retry` is a pipeline-level event and deliberately carries no `stage` key.** It is the only
> pipeline emit whose payload omits it (`reflection.py:129-135`) — because a retry is not a statement
> about one stage, it is a statement about the whole run restarting. A client must therefore handle
> `retry` **before** any stage-based dispatch. The frontend does exactly that, matching on the type and
> returning early before its stage guard, then resetting the seven downstream rows to idle so they
> re-animate on the next pass. Reading `data.stage` first and bailing when it is absent silently drops
> every retry.

### 6.2 The stage-id contract

> [!WARNING]
> **An SSE `stage` id is NOT the graph node name — five of the eight differ.**

| `add_node` name | Emitted `stage` id | Same? |
|---|---|---|
| `planner` | `planner` | ✅ |
| `retrieval` | `retrieval` | ✅ |
| `external_tools` | `external_tools` | ✅ |
| `aggregate` | **`aggregator`** | ❌ |
| `rerank` | **`reranker`** | ❌ |
| `compress` | **`compressor`** | ❌ |
| `reason` | **`reasoning`** | ❌ |
| `reflect` | **`reflection`** | ❌ |

The `stage` id is a **string literal inside a payload dict**, not the event type and not the node name —
which is precisely why it can drift from the `add_node` name unnoticed. **The `emit()` call sites are
the contract, not `workflow.py`.** Renaming a node breaks nothing; changing an `emit(...)` `stage`
literal silently stops the corresponding tracker row updating, with no error and no console warning,
because the client drops any stage id it does not recognise.

### 6.3 Events the route frames, not the pipeline

Four more event types reach the browser without any node emitting them:

| Event | Origin | When |
|---|---|---|
| `done` | the worker thread (`query_routes.py:84`) | the graph returned; carries `{answer, sources, metadata}` |
| `error` | the worker thread's `except` (`query_routes.py:93`) | the graph raised — **in-band, on a `200`** |
| `stream_end` | the generator (`query_routes.py:107`) | the `None` sentinel was drained |
| `error` | the generator (`query_routes.py:111`) | the 180-second per-event wait expired — `{"message": "Stream timeout"}` |

---

## ⚠️ 7. EDGE CASES & GOTCHAS

- **A non-escalating retry cannot produce a different answer.** This is the single most important thing
  to understand about the retry loop, and it is a composition of three facts, each individually
  reasonable. `reflection_feedback` is written on every reflection path and **read by nothing** — no
  node injects it into a prompt, so the retry's prompts are byte-identical to the first pass's. Returned
  keys overwrite, so the retry re-retrieves the same corpus with the same query and gets the same
  documents. And `get_llm()` defaults to `temperature=0` with no node overriding it, so the same prompt
  yields the same completion. **A plain retry therefore re-runs an identical deterministic pipeline and
  gets the identical answer, which the critic then judges identically.** The retry budget only does real
  work when `escalate_external` fires and adds web documents that were not there before. The two
  mechanisms that could break the tie — feedback injection and a non-zero sampling temperature — are
  both absent.

- **Compression usually does not run.** The compressor only calls an LLM when the assembled context
  exceeds `MAX_CONTEXT_CHARS` (default `4000`). At the defaults — `RERANK_TOP_K=5` and `CHUNK_SIZE=500`
  — five chunks total roughly 2 500 characters, so the LLM path rarely fires on document-only context.
  Compression is the exception, not the rule; the stage almost always reports *"Context already within
  limit"* and returns the text verbatim.

- **The compressor's LLM sees at most 10 000 characters.** `full_text[:10_000]` (`compressor.py:79`) is
  a hard cap on what compression can even consider — context beyond it is discarded before the model
  reads it. And `max_chars` is passed as a *prompt instruction*, not enforced: the returned length is
  measured and reported as a ratio but never clipped.

- **The three retrievers do not run in parallel**, despite `hybrid_node.py:4` saying so. The code is
  three sequential synchronous calls (`hybrid_node.py:41-43`) — no thread pool, no `asyncio`. Treat the
  docstring as stale and do not repeat "parallel" as a performance claim.

- **The graph store gets half the retrieval budget.** `graph_store.search(query, top_k=max(TOP_K // 2, 3))`
  — five candidates at the default `RETRIEVAL_TOP_K=10`, against ten each from vector and BM25. The
  asymmetry is deliberate (graph hits are noisier) but it is invisible unless you read that line.

- **The reflection critic can fail open, and that is what prevents an infinite loop.** Its exception
  path sets `grounded: True` **and** `final_answer: answer` (`reflection.py:172-181`), passing an
  unverified answer through as grounded — and because it writes `final_answer`, it also terminates the
  graph. A critic outage degrades quality; it does not wedge the run.

- **A degraded answer shows *more* sources than a successful one.** The happy path filters `sources` to
  the ones the model cited; both reasoning fallbacks (`reasoning.py:113`, `:115`) return the full
  unfiltered list.

- **The direct-answer path returns zero sources by construction.** When the context text is blank, the
  reasoning node makes a plain non-JSON call with the literal prompt *"Answer this question directly
  (no documents available): {query}"* and returns `sources: []` (`reasoning.py:73-83`).

- **Nothing re-reads the environment per request.** Every node reads its tunables with `os.getenv` at
  **module scope**, so they are frozen at import. The LLM cache is likewise never invalidated
  (`llm.py:21`) — a runtime environment change cannot reach an already-constructed instance. Restart
  the process to change a setting.

- **Nodes do not import `Config`.** Only the stores and the registry do. Every node re-declares its own
  literal copy of each default via `os.getenv`. All fourteen duplicated defaults currently agree with
  `config.py`, so this is a **maintenance hazard, not a live bug** — but changing a default in
  `config.py` alone would silently fail to reach the node that re-declares it.

---

## 💥 8. FAILURE MODES

| Failure | Symptom | Pipeline response |
|---|---|---|
| Planner LLM unreachable or returns unparseable output | `stage_error` on the `planner` row | Returns `retrieve=True, use_external=False, query_type="factual"` — degrades to plain RAG |
| A retrieval store raises | **No `stage_error`** — the exception escapes the node | Propagates out of `rag_graph.invoke()` into the route's `except`, reaching the browser as an in-band `error` event on a `200`. `retrieval` is the only node with no error path of its own |
| `ddgs` not installed | `stage_error` on `external_tools`, `"duckduckgo-search not installed"` | Returns `{"web_docs": []}` — web failure is always non-fatal |
| Web search raises for any other reason | `stage_error` on `external_tools` | Returns `{"web_docs": []}` |
| Cross-encoder model cannot load or predict | `stage_error` on `reranker` | Falls back to sorting `all_docs` by raw `score` — **and this breaks two things at once, see the callout below** |
| No documents at all reach the reranker | `stage_complete` with *"No documents to rerank"* | `context` is `[]`; reasoning takes its no-context direct-answer branch |
| Compression LLM fails | `stage_error` on `compressor` | Returns `full_text[:MAX_CONTEXT_CHARS]` — a hard truncation, not a compression |
| Reasoning JSON unparseable | `stage_error` on `reasoning` | A **second, plainer LLM attempt** with a 3 000-char context prompt; if that also raises, `"Unable to generate an answer."` |
| Reflection LLM fails | `stage_error` on `reflection` | **Fails open** — `grounded: True`, `final_answer: answer`, `pipeline_metadata: {"error": …}`, and the graph terminates |
| Browser disconnects mid-run | Stream closes | **The compute is not freed.** The daemon thread runs to completion; `emit()` becomes a no-op once the session is closed |
| A single event takes over 180 s | `error` event `{"message": "Stream timeout"}`, then the stream closes | Frees the *browser*, never the thread |

> [!CAUTION]
> **A broken reranker silently disables web-search escalation too — two features fail from one cause.**
> The fallback path sorts on the incomparable raw `score`
> (`fallback = sorted(all_docs, key=lambda d: d.get("score", 0), reverse=True)[:RERANK_TOP_K]`,
> `reranker.py:74`), so BM25's unbounded scale dominates the selection and a strong cosine match at
> `0.9` loses to a mediocre BM25 hit at `7.4`. Worse, those fallback documents keep the
> `rerank_score: 0.0` their stores seeded — so the escalation test `max_rerank < 0` evaluates
> `0.0 < 0` → `False`, `kb_insufficient` is never true, and the pipeline stops escalating to web search
> exactly when its local ranking is at its least trustworthy. The only visible signal is one
> `stage_error` on the reranker row.

**Two known limitations, both with named triggers.** Neither is a hang, and neither is speculative:

1. **An empty `answer` loops the graph without spending retry budget.** When `answer` is falsy, the
   reflection node returns early (`reflection.py:69-74`) with `grounded: False` and an unchanged
   `retry_count` — setting **no `final_answer`**. The router therefore sends control back to
   `retrieval`, and because the early return sits *above* the budget check at `reflection.py:97`, the
   budget is never consulted. The realistic trigger is a small local model emitting `"answer": ""` in
   its JSON, which `result.get("answer", "No answer generated.")` returns unchanged because the key is
   present. Each iteration costs four LLM calls and re-emits `stage_start` with `"attempt": 1`, so the
   tracker shows a frozen attempt counter. The only in-graph bound is LangGraph's recursion limit,
   which this code never sets — `rag_graph.invoke(initial_state)` passes no `config`. **The installed
   LangGraph is 1.2.11, whose default recursion limit is `10007`**, not the widely-quoted `25`; since
   `pyproject.toml` pins only `langgraph>=0.1.0`, the effective ceiling is resolved-version-dependent.
   In practice the 180-second SSE timeout ends the *stream* long before that — but it does not end the
   compute.

2. **Switching `VECTOR_BACKEND` does not migrate data.** It silently exposes a different, probably
   empty, index. See [`../hybrid-retrieval/stores.md`](../hybrid-retrieval/stores.md).

---

## 🧩 9. EXTENSION POINTS

**Add a node.** Create `custom_packages/rag_pipeline/<phase>/<name>.py` with the `def <name>_node(state:
RAGState) -> dict` signature, a module docstring ending in an `Emits:` line, and a `stage_start` /
`stage_complete` pair. Register it in `workflow.py` with `builder.add_node(...)` and wire its edges.
Then — and this is the step that is easy to miss — **add its emitted `stage` id to the frontend's
`STAGES` list**, because the id in your `emit()` payload is what the tracker matches, not the node name
you chose (§6.2).

**Add a state key.** Declare it in `RAGState` (`state.py`) *and* seed it in the route's
`initial_state` (`query_routes.py:54-79`), so no key first appears mid-run. `TypedDict` is not enforced
at runtime — a misspelled key is merged into the state silently — so treat the declaration as
documentation and the seed as the real contract. See [`state-model.md`](state-model.md) §4.

**Add a retrieval backend.** Implement the store surface under `retrieval/stores/<name>_store.py`, add
its search call to `hybrid_node.py`, add its list to `RAGState`, and append it to the aggregator's
concatenation. Details and the exact surface to copy are in
[`../hybrid-retrieval/README.md`](../hybrid-retrieval/README.md) §9.

**Change the retry policy.** The budget is `MAX_REFLECTION_RETRIES` (default `2`), read at
`reflection.py:21`. Do **not** edit `workflow.py:33` — it is dead code (§4.3). If you want a retry to
behave differently from its predecessor, the change is not in the budget: it is in feeding
`reflection_feedback` into the reasoning or retrieval prompts, or in raising the temperature. Without
one of those, extra retries only cost LLM calls (§7).

**Change the escalation rule.** The heuristic is three lines at `reflection.py:99-104`. If you change
`RERANKER_MODEL`, re-derive the `< 0` threshold against the new model's score range first.

**What not to touch.** Do not add a second writer of `final_answer` — that key is the termination
signal, and a stray write ends the graph from wherever it happens. Do not make `emit()` raise on an
unknown session; a disconnected browser would become a pipeline crash. Do not run more than one worker
process (§10).

---

## 🔗 10. RELATED DECISIONS & DEEPER READING

- **LangGraph over a hand-rolled chain.** The pipeline needs a conditional entry point and a bounded
  loop, both of which a linear chain expresses badly. A state machine makes the branch points explicit
  and reviewable — the two routers are ten lines of pure function — and makes the retry a first-class
  edge rather than a `while` loop buried in a service. The cost is that the shared state is a plain
  `TypedDict` with no runtime validation, which is why the merge semantics get their own page.

- **One shared `TypedDict` instead of per-node models.** Every node reads what it needs and returns only
  what it changed; there are no per-node input/output schemas to keep in sync. The trade is that a
  typo'd return key is merged silently and the correctly-spelled key keeps its old value — a class of
  bug a static type checker would catch, and this repo runs none.

- **One worker, one process — always.** The session registry `_sessions` is a plain module dict and
  every store is a module singleton. Forking splits the SSE producer from its consumer *and* gives each
  worker a divergent in-memory BM25 and graph copy. This is why the dev server runs `threaded=True` and
  the production command carries `-w 1`.

- **Errors are in-band by necessity, not preference.** The response headers are sent the moment
  streaming begins, so a node failing at second 30 cannot become a `500`. The pipeline therefore reports
  failures as events on a `200`, and every node except `retrieval` catches its own exceptions and
  degrades rather than propagating.

- **Prompt input is unescaped by design.** Query text, retrieved chunks and web-search results are
  interpolated straight into the planner, compressor, reasoning and reflection prompts. Prompt
  injection from a crafted document — including against the reflection agent that judges grounding — is
  an accepted, documented risk on a localhost-only deployment. Do not widen it.

**Continue reading:**

- [`nodes.md`](nodes.md) — the per-node reference for all eight nodes
- [`state-model.md`](state-model.md) — `RAGState`, merge semantics, and the invariants
- [`../hybrid-retrieval/README.md`](../hybrid-retrieval/README.md) — the three-store retrieval subsystem
- [`../hybrid-retrieval/stores.md`](../hybrid-retrieval/stores.md) — vector, BM25 and graph internals
- [`../../../Frontend/Documentation/chat/pipeline-tracker.md`](../../../Frontend/Documentation/chat/pipeline-tracker.md) — the eight-row tracker these nodes drive, and why the emitted id is the contract
