<div align="center">

# 🧬 adRAG

### Multi-stage RAG pipeline — hybrid search, reranking, and self-reflection for grounded answers.

<br>

[![Version](https://img.shields.io/badge/version-1.0.0-7c5cff)](Frontend/package.json)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776ab?logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0%2B-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.1%2B-1c3c3c)](https://langchain-ai.github.io/langgraph/)

[![Vue](https://img.shields.io/badge/Vue-3.4-42b883?logo=vuedotjs&logoColor=white)](https://vuejs.org/)
[![Tailwind](https://img.shields.io/badge/Tailwind-3.4-06b6d4?logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![Providers](https://img.shields.io/badge/LLM-OpenAI%20%7C%20Ollama-f59e0b)](#%EF%B8%8F-9-configuration)
[![Status](https://img.shields.io/badge/status-active-3fb950)](#)

</div>

<br>

---

<br>

## Content Tree

<pre>
adRAG
│
├── <a href="#-1-overview">📖 1. Overview</a>
│
├── <a href="#-2-features">✨ 2. Features</a>
│
├── <a href="#-3-how-it-works">🧠 3. How it works</a>
│   ├── <a href="#31-system-architecture">3.1 System architecture</a>
│   ├── <a href="#32-the-pipeline">3.2 The pipeline</a>
│   ├── <a href="#33-the-three-retrieval-stores">3.3 The three retrieval stores</a>
│   └── <a href="#34-the-reflection-loop">3.4 The reflection loop</a>
│
├── <a href="#%EF%B8%8F-4-tech-stack">🛠️ 4. Tech stack</a>
│
├── <a href="#-5-project-structure">📁 5. Project structure</a>
│
├── <a href="#-6-getting-started">🚀 6. Getting started</a>
│   ├── <a href="#61-prerequisites">6.1 Prerequisites</a>
│   ├── <a href="#62-run-the-backend">6.2 Run the backend</a>
│   ├── <a href="#63-run-the-frontend">6.3 Run the frontend</a>
│   └── <a href="#64-your-first-query">6.4 Your first query</a>
│
├── <a href="#-7-usage">💡 7. Usage</a>
│
├── <a href="#-8-api">🔌 8. API</a>
│
├── <a href="#%EF%B8%8F-9-configuration">⚙️ 9. Configuration</a>
│
├── <a href="#%EF%B8%8F-10-known-gaps">⚠️ 10. Known gaps</a>
│
├── <a href="#-11-documentation">📚 11. Documentation</a>
│
└── <a href="#%EF%B8%8F-12-roadmap">🗺️ 12. Roadmap</a>
</pre>

<br>

---

<br>

## 📖 1. OVERVIEW

**adRAG** is a multi-stage Retrieval-Augmented Generation pipeline that combines **hybrid search**
(vector + BM25 + graph), **cross-encoder reranking**, and a **self-reflection agent** to generate
grounded, cited answers from your own documents.

It ships as two independently runnable halves:

- **Backend** — a Flask REST + Server-Sent Events API wrapped around an eight-node **LangGraph**
  pipeline. It ingests documents, retrieves over three stores, reranks, compresses context, and
  generates an answer that is checked for grounding before it is returned.
- **Frontend** — a **Vue 3** single-page app that drives the pipeline and renders its progress live
  from the SSE stream: chat, knowledge-base management, and LLM provider configuration.

The problem it targets is the one every naive RAG system hits — a single similarity search returns
plausible-looking chunks, the model answers from them regardless of whether they support the claim,
and nobody can tell where the answer came from. adRAG attacks that from three sides: it retrieves the
same corpus three different ways so keyword-exact and entity-linked evidence survives alongside
semantic matches, it reranks the merged pool with a cross-encoder that reads the query and the
passage together, and it re-reads its own answer against the evidence before shipping it.

> [!NOTE]
> Everything runs locally against your own store. The LLM is either **OpenAI** or a local **Ollama**
> server — chosen per request — and web search (DuckDuckGo) is optional and needs no API key.

<br>

---

<br>

## ✨ 2. FEATURES

- 🔍 **Hybrid retrieval over three stores** — a dense vector index (ChromaDB by default, FAISS opt-in),
  a BM25 keyword index, and a NetworkX knowledge graph, all queried on every retrieval pass.
- 🧭 **A Self-RAG planner** — an LLM decision node that first decides *whether* retrieval is needed at
  all, whether to reach for external tools, and what kind of query it is (`factual`, `analytical`,
  `conversational`).
- 🎯 **Cross-encoder reranking** — `cross-encoder/ms-marco-MiniLM-L-6-v2` scores every
  `(query, document)` pair and keeps the top 5, with a graceful fall-back to score-sorted results if
  the model fails to load.
- 🗜️ **Threshold-triggered context compression** — evidence passes through untouched below
  `MAX_CONTEXT_CHARS` (4000); only above it does an LLM compression pass run.
- 🔁 **A bounded self-reflection loop** — the answer is graded for grounding, and a failed grade
  triggers up to `MAX_REFLECTION_RETRIES` (2) more attempts, for at most three passes in total.
- 🌐 **Automatic web-search escalation** — when a retry follows an empty or irrelevant knowledge-base
  hit, reflection turns on DuckDuckGo search for the next attempt.
- 📡 **Live pipeline streaming** — ten Server-Sent Event types report every stage start, completion,
  skip, error, and retry as it happens, so the UI shows the pipeline working rather than a spinner.
- 🧾 **Cited answers** — the generator emits inline `[1]`, `[2]` citations and the source list is
  filtered down to only the documents it actually cited.
- 🔌 **Dual LLM providers** — OpenAI or Ollama, selected per request, with a live availability probe
  and model list behind `GET /api/providers`.
- 📚 **Knowledge-base management** — upload `.pdf` / `.txt` / `.md` / `.docx` (up to 50 MB), list what
  is indexed, delete a single knowledge base, or clear everything; re-uploading the same file replaces
  its data instead of duplicating it.

<br>

---

<br>

## 🧠 3. HOW IT WORKS

### 3.1 System architecture

The browser never talks to a store directly. The Vue SPA calls the Flask API, Flask runs the compiled
LangGraph pipeline on a background thread, and every stage the pipeline enters is pushed back to the
browser over one long-lived SSE response.

<p align="center">
  <img src=".readme-lib/readme/diagrams/svg/system-architecture.svg" alt="Architecture map: the Vue 3 SPA on localhost:8080 calls the Flask API on localhost:5000 through the dev proxy; Flask runs the LangGraph pipeline on a daemon thread, whose retrieval node queries the Chroma/FAISS, BM25 and NetworkX stores, whose external_tools node calls DuckDuckGo, and whose LLM nodes call OpenAI or Ollama; the pipeline emits into a per-query SSE session queue that streams back to the browser." width="760">
</p>

<sub>Diagram source: <a href=".readme-lib/readme/diagrams/mermaid-source/system-architecture.mmd"><code>system-architecture.mmd</code></a> — edit it, then regenerate the SVG (don't hand-edit the SVG).</sub>

The moving parts:

| Piece | Where it runs | Responsibility |
|---|---|---|
| Vue 3 SPA | `localhost:8080` (dev server) | Four routes, twelve components, two Pinia stores; renders the live pipeline |
| Dev proxy | Vue CLI dev server | Forwards `/api/*` to `http://localhost:5000`, so the SPA has no CORS hop in development |
| Flask API | `0.0.0.0:5000`, threaded | Eight `/api` routes; owns upload, store queries, and the SSE session |
| LangGraph pipeline | Daemon thread per query | The eight nodes; compiled once into a module-level `rag_graph` singleton |
| Stores | On disk under `Backend/data/databases/` | Chroma or FAISS, BM25, and the NetworkX graph — each a process-wide singleton |
| LLM providers | OpenAI API or a local Ollama server | Chosen per request; instances cached by provider, temperature, JSON mode, and model |

SSE mechanics: each query gets a `uuid4` session id mapped to a `queue.Queue`. The pipeline runs in a
daemon thread and emits into that queue; the HTTP response drains the queue with a **180-second**
timeout and closes on a `None` sentinel, sending a literal `stream_end` frame last. The response
carries `Cache-Control: no-cache`, `X-Accel-Buffering: no`, and `Connection: keep-alive` so no
intermediary buffers the stream.

### 3.2 The pipeline

Eight nodes, registered in order as `planner`, `retrieval`, `external_tools`, `aggregate`, `rerank`,
`compress`, `reason`, `reflect`. Entry is `planner`; two of the edges are conditional.

<p align="center">
  <img src=".readme-lib/readme/diagrams/svg/rag-pipeline-flow.svg" alt="Pipeline flow: a user query enters the planner, which branches three ways — to retrieval, straight to external_tools, or straight to aggregate; retrieval flows into external_tools, then the linear spine aggregate, rerank, compress, reason; reflect then either returns the cited answer or loops back to retrieval for up to two retries." width="360">
</p>

<sub>Diagram source: <a href=".readme-lib/readme/diagrams/mermaid-source/rag-pipeline-flow.mmd"><code>rag-pipeline-flow.mmd</code></a> — edit it, then regenerate the SVG (don't hand-edit the SVG).</sub>

The routing rules, exactly:

- **`planner` is a three-way branch.** `retrieve = true` goes to `retrieval`; otherwise
  `use_external = true` goes straight to `external_tools`; otherwise it skips both and goes to
  `aggregate`.
- **`retrieval` always flows into `external_tools`**, which self-skips (emitting a skip event) when
  `use_external` is false.
- **The spine is linear** from there: `external_tools` → `aggregate` → `rerank` → `compress` →
  `reason` → `reflect`.
- **`reflect` is the second conditional edge.** If a `final_answer` has been set, the graph ends;
  otherwise it loops back to `retrieval` for another attempt.

What each node actually does:

| Node | Behaviour |
|---|---|
| `planner` | Self-RAG decision. The LLM returns JSON `{retrieve, use_external, query_type, reasoning}`. On any exception it fails safe to `retrieve=true`, `use_external=false`, `query_type="factual"`. |
| `retrieval` | Queries all three stores sequentially in one function — vector, BM25, and graph — each with `RETRIEVAL_TOP_K` (10); the graph store uses `max(TOP_K // 2, 3)`. |
| `external_tools` | DuckDuckGo web search, no API key, five results. Imports `ddgs` and falls back to the legacy `duckduckgo_search` package; on `ImportError` or any exception it degrades to an empty result set rather than failing the query. |
| `aggregate` | Merges vector, BM25, graph, and web results, deduplicates by **MD5 of the content** keeping the highest-scoring copy, and sorts by score descending. |
| `rerank` | Cross-encoder scores every `(query, document)` pair, sorts, and keeps `RERANK_TOP_K` (5). The model is a lazy singleton; on failure it falls back to the score-sorted top-k. |
| `compress` | Builds numbered `[n] label` + content blocks. If the total is at or below `MAX_CONTEXT_CHARS` it passes through **unchanged** — the compression LLM only runs above the threshold, and its input is truncated to 10 000 characters. |
| `reason` | Generates JSON `{answer, confidence, cited_sources, key_facts, is_sufficient}` with inline `[1]`, `[2]` citations, then filters the source list down to the ones actually cited. With no context at all it takes a direct-answer path. |
| `reflect` | Grades the answer: `{grounded, confidence, issues, feedback, should_retry}`. It retries only when the answer is **not** grounded, `should_retry` is true, **and** the retry budget is unspent. A non-grounded final answer gets a caveat line appended. |

### 3.3 The three retrieval stores

Every retrieval pass hits all three. They find different things on purpose — semantic neighbours,
exact terms, and entity-linked neighbours — and the aggregator merges them.

| Store | Library | What it finds | `source` tag | Persistence |
|---|---|---|---|---|
| Dense vector (default) | ChromaDB `PersistentClient`, collection `rag_documents`, cosine space | Semantic similarity | `vector` | On-disk Chroma directory at `CHROMA_PATH` |
| Dense vector (opt-in) | FAISS `IndexFlatIP` over L2-normalised vectors, which is cosine similarity | Semantic similarity | `vector` | Pickle plus an `.idx` sidecar at `FAISS_PATH` |
| Sparse keyword | `rank_bm25.BM25Okapi` over lower-cased `\b\w+\b` tokens | Exact term and keyword overlap; only results scoring above zero are returned | `bm25` | Pickled corpus and metadata at `BM25_PATH`; the index is rebuilt on load |
| Knowledge graph | NetworkX `nx.Graph`, bipartite document ↔ entity | Entity-linked chunks via a two-hop traversal — first hop weighted ×2.0, second hop +0.5 | `graph` | Pickled graph and document store at `GRAPH_PATH` |

Three details worth knowing before you extend any of this:

- **Entity extraction is regex, not an LLM.** The graph store picks up multi-word proper nouns,
  two-to-six-character acronyms, and camelCase identifiers, then subtracts a 25-word stop list. It is
  cheap and deterministic — and it will not find entities that don't look like those three shapes.
- **All three stores are process-wide singletons**, guarded in `__new__`, as is the
  `SentenceTransformer` embedder (created lazily on first use).
- **Selecting `faiss` without the package installed raises a `RuntimeError` at import.** The switch is
  `VECTOR_BACKEND`, and `faiss-cpu` is an optional dependency.

Deleting a knowledge base prunes its chunks from all three stores and also removes entity nodes in the
graph that no longer link to any document.

### 3.4 The reflection loop

Reflection is what separates this pipeline from a one-shot RAG chain. After `reason` produces an
answer, `reflect` grades it against the retrieved evidence and decides whether the pipeline is done.

- **The verdict** is JSON: `{grounded, confidence, issues, feedback, should_retry}`.
- **The retry condition** is a conjunction — the answer must be **not grounded**, reflection must set
  `should_retry`, and `retry_count` must still be below `MAX_RETRIES`.
- **The budget** is `MAX_REFLECTION_RETRIES`, default `2`, which means **at most three passes** in
  total.
- **Escalation to the web is conditional and evidence-driven.** On a retry, if the knowledge base
  looked insufficient — zero context documents, or a maximum rerank score below zero — and
  `use_external` was false, reflection flips it to true so the next attempt adds web search. The
  negative-score test is deliberate: the ms-marco cross-encoder returns negative logits for pairs it
  considers irrelevant, so "the best passage scored below zero" is a usable signal that the corpus
  simply doesn't contain the answer.
- **When the budget runs out**, the answer is still returned — with a caveat line appended noting it
  could not be fully grounded.

<br>

---

<br>

## 🛠️ 4. TECH STACK

**Backend** — Python 3.10+ is a hard requirement, not a preference: the source uses PEP 604 unions
(`str | None`) evaluated at runtime in signatures, with no `from __future__ import annotations`
anywhere. Pins below are the exact lower bounds from `Backend/requirements.txt`.

| Role | Package | Minimum |
|---|---|---|
| Web API | `flask` · `flask-cors` | `>=3.0.0` · `>=4.0.0` |
| Config | `python-dotenv` | `>=1.0.0` |
| Pipeline | `langgraph` | `>=0.1.0` |
| LLM abstraction | `langchain` · `langchain-text-splitters` · `langchain-community` | `>=0.2.0` (each) |
| Provider bindings | `langchain-openai` · `langchain-ollama` | `>=0.1.0` (each) |
| Dense vector store | `chromadb` (default) · `faiss-cpu` (optional) | `>=0.5.0` · `>=1.7.4` |
| Embeddings + reranking | `sentence-transformers` | `>=3.0.0` |
| Sparse retrieval | `rank-bm25` | `>=0.2.2` |
| Knowledge graph | `networkx` | `>=3.3` |
| Document loaders | `pypdf` · `docx2txt` · `unstructured` | `>=4.0.0` · `>=0.8` · `>=0.14.0` |
| Web search | `ddgs` | `>=7.0.0` |
| Utilities | `numpy` · `requests` | `>=1.26.0` · `>=2.31.0` |

**Frontend** — Vue CLI 5 / webpack (not Vite), from `Frontend/package.json`. Node.js 18 or newer is
what the frontend documentation calls for; nothing in the manifest pins an engine.

| Role | Package | Version |
|---|---|---|
| Framework | `vue` | `^3.4.0` |
| Routing | `vue-router` | `^4.6.4` |
| State | `pinia` | `^2.1.7` |
| HTTP | `axios` | `^1.7.0` |
| Markdown rendering | `marked` | `^12.0.0` |
| Build | `@vue/cli-service` · `@vue/cli-plugin-babel` | `^5.0.8` (each) |
| Styling | `tailwindcss` · `postcss` · `autoprefixer` | `^3.4.0` · `^8.4.0` · `^10.4.0` |

**Models** — every default is overridable by environment variable:

| Purpose | Default | Variable |
|---|---|---|
| OpenAI chat model | `gpt-4o-mini` | `LLM_MODEL` |
| Ollama chat model | `llama3.2` (server at `http://localhost:11434`) | `OLLAMA_MODEL` |
| Embeddings | `all-MiniLM-L6-v2` | `EMBEDDING_MODEL` |
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` | `RERANKER_MODEL` |

<br>

---

<br>

## 📁 5. PROJECT STRUCTURE

```text
Advanced RAG System/
│
├── 📁 Backend/                         Flask + LangGraph RAG API (Python)
│   ├── 📁 documentation/               API, architecture & pipeline docs
│   │
│   ├── 📁 src/                         Application source
│   │   ├── 📁 rag_pipeline/            The 8-node LangGraph pipeline
│   │   │   ├── 📁 core/                SSE event bus — queues, emit()
│   │   │   ├── 📁 encoding/            LLM factory + embedding singleton
│   │   │   ├── 📁 generation/          Planner, compressor, reasoning, reflection
│   │   │   ├── 📁 ingestion/           Loader/chunker + KB registry
│   │   │   ├── 📁 ranking/             Aggregator + cross-encoder reranker
│   │   │   ├── 📁 retrieval/           vector/ · keyword/ · graph/ · web search
│   │   │   ├── 📄 graph.py             Workflow builder — the rag_graph singleton
│   │   │   └── 📄 state.py             RAGState TypedDict — shared pipeline state
│   │   │
│   │   ├── 📄 app.py                   Flask app + all 8 /api routes
│   │   ├── 📄 config.py                Environment-driven configuration
│   │   └── 📄 main.py                  Dev entry point — python src/main.py
│   │
│   ├── 📄 .env.example                 Backend env template — copy to .env
│   ├── 📄 README.md                    Backend quickstart
│   └── 📄 requirements.txt             Python dependencies
│
├── 📁 Frontend/                        Vue 3 SPA (Vue CLI / webpack)
│   ├── 📁 documentation/               Component & state docs
│   ├── 📁 public/                      index.html shell
│   │
│   ├── 📁 src/                         Application source
│   │   ├── 📁 assets/                  main.css — global stylesheet
│   │   ├── 📁 components/              12 components (NavBar, QueryInput…)
│   │   ├── 📁 router/                  4 lazy-loaded routes
│   │   ├── 📁 services/                api.js — REST calls + SSE streaming
│   │   ├── 📁 stores/                  Pinia stores — rag.js, ui.js
│   │   ├── 📁 views/                   Home · Chat · KnowledgeBase · Config
│   │   ├── 📄 App.vue                  Root layout
│   │   └── 📄 main.js                  Bootstrap — Vue + Pinia + Router
│   │
│   ├── 📄 .env.example                 Frontend env template — VUE_APP_API_URL
│   ├── 📄 package.json                 Scripts + dependencies
│   ├── 📄 postcss.config.js            PostCSS configuration
│   ├── 📄 README.md                    Frontend quickstart
│   ├── 📄 tailwind.config.js           Tailwind configuration
│   └── 📄 vue.config.js                Dev server :8080 + /api proxy → :5000
│
├── 📁 .readme-lib/                     Doc asset library — icons & diagrams
└── 📄 .gitignore                       Ignored paths — data, secrets, symlinks
```

Runtime data lives under `Backend/data/` (`uploads/` for the original files, `databases/` for the three
stores and the knowledge-base registry). It does not exist in a fresh checkout — the backend creates it
on first run, and it is gitignored.

<br>

---

<br>

## 🚀 6. GETTING STARTED

The two halves run independently. Start the backend first; the frontend dev server proxies to it.

### 6.1 Prerequisites

| Requirement | Why |
|---|---|
| **Python 3.10+** | The backend uses PEP 604 `X \| Y` unions evaluated at runtime |
| **Node.js 18+** | What the frontend documentation calls for; no engine is pinned in the manifest |
| **An OpenAI API key** *or* **a running Ollama server** | The pipeline needs at least one working LLM provider |

Ollama, if you use it, is expected at `http://localhost:11434`. No key is needed for web search —
DuckDuckGo is queried without one.

Clone the repository first:

```bash
git clone git@github.com:Shohrab-Hossain/Advanced-RAG-System.git
cd Advanced-RAG-System
```

The two halves are independent — each gets its own terminal, and the backend should be running before
the frontend is useful.

### 6.2 Run the backend

```bash
cd Backend
python -m venv .venv
```

Activate the environment — `.venv\Scripts\activate` on Windows, `source .venv/bin/activate` on
macOS and Linux — then install and configure:

```bash
pip install -r requirements.txt
cp .env.example .env
```

Open `.env` and set your key (the template already uses a placeholder of this shape):

```bash
OPENAI_API_KEY=sk-...
```

Then start it:

```bash
python src/main.py
```

The API listens on `0.0.0.0:5000` with threading enabled; debug mode follows `FLASK_DEBUG`. Confirm it
is up:

```bash
curl http://localhost:5000/api/health
```

```json
{ "status": "ok", "version": "1.0.0" }
```

### 6.3 Run the frontend

In a second terminal:

```bash
cd Frontend
npm install
npm run serve
```

The dev server comes up on `http://localhost:8080` and proxies `/api` to `http://localhost:5000` with
`changeOrigin` set, so no CORS configuration is needed in development. To build a static bundle
instead, run `npm run build`.

> [!TIP]
> Pointing the SPA at a backend somewhere other than the dev proxy is a one-line change: copy
> `Frontend/.env.example` and set `VUE_APP_API_URL`. Left unset, the client uses an empty base URL and
> relies on the proxy.

### 6.4 Your first query

1. Open `http://localhost:8080` and go to **Knowledge Base**.
2. Upload a `.pdf`, `.txt`, `.md`, or `.docx` file — up to 50 MB. It is chunked (500 characters,
   50-character overlap) and indexed into all three stores; the response reports how many chunks,
   vectors, entities, and edges it produced.
3. Go to **Chat** and ask a question about the document.
4. Watch the pipeline tracker. Each of the eight stages reports as it starts and finishes, the
   retrieval stage reports per-store hit counts, and the answer arrives with numbered citations.

Uploading the same file again is safe: the backend deletes that file hash's data from all three stores
and the registry before re-indexing, so nothing is duplicated.

<br>

---

<br>

## 💡 7. USAGE

The SPA has four routes, all lazy-loaded, using HTML5 history mode:

| Route | Page | What you do there |
|---|---|---|
| `/` | Home | The pitch and the entry point into the app |
| `/chat` | Chat | Ask questions, watch the live pipeline, read cited answers |
| `/knowledge-base` | Knowledge Base | Upload documents, review what is indexed, delete a KB or clear everything |
| `/configuration` | Configuration | Pick the provider and model; see which providers are actually available |

Chat history is kept in `localStorage` under the key `rag-chat-history`, capped at 50 entries.

**Querying from the command line.** `POST /api/query` answers with an SSE stream, so pass `-N` to stop
curl from buffering:

```bash
curl -N -X POST http://localhost:5000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What does the reflection node check?", "provider": "openai"}'
```

Frames arrive as `data: <json>` blocks, each carrying a `type` and a `data` object — abridged:

```text
data: {"type": "stage_start", "data": {"stage": "planner", "message": "…"}}

data: {"type": "retrieval_result", "data": {"stage": "retrieval", "vector_count": 10, "bm25_count": 4, "graph_count": 3, "message": "…"}}

data: {"type": "stage_complete", "data": {"stage": "reranker", "message": "…"}}

data: {"type": "done", "data": {"answer": "…", "sources": [], "metadata": {}}}

data: {"type": "stream_end"}
```

`provider` is optional — omit it and `DEFAULT_PROVIDER` applies. `model` is optional too. The full
event vocabulary is in [§8](#-8-api).

> [!NOTE]
> The browser client does **not** use `EventSource`. Because the query has to be sent as a POST body,
> the SPA streams the response with `fetch` plus a `ReadableStream` reader, and returns an `abort`
> handle so an in-flight query can be cancelled.

<br>

---

<br>

## 🔌 8. API

Eight endpoints, all under `/api`. CORS allows `FRONTEND_URL`, `http://localhost:3000`, and
`http://localhost:8080`, for the methods `GET`, `POST`, `DELETE`, and `OPTIONS`.

| Method | Path | What it does |
|---|---|---|
| `POST` | `/api/query` | Runs the pipeline and streams it back as `text/event-stream`. Body `{query, provider?, model?}`. Returns `400` if `query` is missing or empty, or if `provider` is anything other than `openai` or `ollama`. |
| `POST` | `/api/upload` | Multipart `file` upload; chunks and indexes into all three stores. Returns `{success, file_name, file_hash, chunks_indexed, kb, stats}`. `400` for a missing file field, an empty filename, or a disallowed extension; `422` when no text could be extracted; `500` on an indexing failure. |
| `GET` | `/api/documents` | Index counts — `{vector_count, bm25_count, graph}`. |
| `DELETE` | `/api/clear` | Wipes all three stores and the registry **and** deletes the uploaded files from disk. Returns `{success, message}`. |
| `GET` | `/api/knowledge-bases` | Lists the indexed knowledge bases — `{knowledge_bases: [...]}`. |
| `DELETE` | `/api/knowledge-bases/<file_hash>` | Removes one knowledge base from all three stores and deletes its file. Returns `{success, stats}`. |
| `GET` | `/api/providers` | `{providers: [openai, ollama], default}`. OpenAI's `available` flag reflects whether an API key is set; Ollama is probed live. The OpenAI model list offered is `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`, `gpt-3.5-turbo`; Ollama's list comes from the server itself. |
| `GET` | `/api/health` | `{"status": "ok", "version": "1.0.0"}`. |

The Ollama probe is a `GET` to `{OLLAMA_BASE_URL}/api/tags` with a five-second timeout, falling back to
a ping at the server root.

**SSE event reference.** There are **ten** wire types. Seven are emitted by pipeline nodes; `done`,
`error`, and `stream_end` are stream-control frames produced by the Flask layer, not by any node.

| `type` | Emitted by | Key `data` fields |
|---|---|---|
| `stage_start` | All eight nodes | `stage`, `message` — plus `attempt` and `max_attempts` on the reflection stage |
| `stage_complete` | Seven nodes | `stage`, `message`, plus node-specific fields |
| `stage_error` | Seven nodes | `stage`, `error` |
| `stage_skip` | The retrieval and web-search stages | `stage`, `message` — retrieval skipped for a direct answer, or web search not needed |
| `retrieval_result` | The retrieval stage | `stage`, `vector_count`, `bm25_count`, `graph_count`, `message` |
| `retry` | The reflection stage | `attempt`, `max_attempts`, `reason`, `escalate_external`, `message` — **no `stage` field** |
| `finalize` | The reflection stage | `stage`, `grounded`, `message` |
| `done` | The Flask layer | `answer`, `sources`, `metadata` |
| `error` | The Flask layer | `message`, `stage` — `stage` is `pipeline` for an unhandled pipeline exception, and this type is also what a stream timeout reports |
| `stream_end` | The Flask layer | None — it is written to the stream as the literal `data: {"type": "stream_end"}` and carries no `data` object |

**Stage labels are not the graph node ids.** The `stage` field takes one of eight values: `planner`,
`retrieval`, `external_tools`, `aggregator`, `reranker`, `compressor`, `reasoning`, `reflection`. Four
of those differ from the LangGraph node names in [§3.2](#32-the-pipeline) — `aggregate`, `rerank`,
`compress`, and `reflect` — so match on the labels above when you consume the stream. The frontend's
stage list uses these same eight.

Full request and response bodies live in
[`Backend/documentation/api.md`](Backend/documentation/api.md).

> [!WARNING]
> The SSE table in `Backend/documentation/api.md` has drifted from the code: it lists nine event types
> (it is missing `error`), shows a `web_count` field on `retrieval_result` that the emitter does not
> send, and shows a `stage` field on `retry` that is not there. The table above was enumerated from the
> emit sites — trust it over the older one.

<br>

---

<br>

## ⚙️ 9. CONFIGURATION

The backend reads `Backend/.env`. Copy `Backend/.env.example` and change what you need — everything
has a working default except the OpenAI key.

| Variable | Default | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | *(empty)* | Your OpenAI key. Empty means the OpenAI provider reports itself unavailable. |
| `LLM_MODEL` | `gpt-4o-mini` | OpenAI chat model |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Where the Ollama server lives |
| `OLLAMA_MODEL` | `llama3.2` | Ollama chat model |
| `DEFAULT_PROVIDER` | `openai` | Provider used when a request doesn't name one |
| `VECTOR_BACKEND` | `chroma` | `chroma` or `faiss`; `faiss` requires `faiss-cpu` |
| `PORT` | `5001` | Backend listen port — but `Backend/.env.example` sets `PORT=5000`, so a `.env` copied from it lands on 5000. See [§10](#%EF%B8%8F-10-known-gaps). |

<details>
<summary><b>Full reference — every environment variable and non-env constant</b></summary>

<br>

**Providers and models**

| Variable | Default |
|---|---|
| `OPENAI_API_KEY` | *(empty)* |
| `LLM_MODEL` | `gpt-4o-mini` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` |
| `OLLAMA_MODEL` | `llama3.2` |
| `DEFAULT_PROVIDER` | `openai` |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` |
| `RERANKER_MODEL` | `cross-encoder/ms-marco-MiniLM-L-6-v2` |

**Pipeline tuning**

| Variable | Default | Effect |
|---|---|---|
| `RETRIEVAL_TOP_K` | `10` | Results requested from each store per pass |
| `RERANK_TOP_K` | `5` | Documents kept after cross-encoder reranking |
| `MAX_CONTEXT_CHARS` | `4000` | Compression only runs above this total |
| `MAX_REFLECTION_RETRIES` | `2` | Extra attempts after a failed grounding check |
| `CHUNK_SIZE` | `500` | Characters per chunk at ingestion |
| `CHUNK_OVERLAP` | `50` | Character overlap between adjacent chunks |

**Paths**

| Variable | Default |
|---|---|
| `DATA_ROOT` | `./data` |
| `UPLOAD_FOLDER` | `<DATA_ROOT>/uploads` |
| `DATABASE_ROOT` | `<DATA_ROOT>/databases` |
| `CHROMA_PATH` | `<DATABASE_ROOT>/vector_db/chroma_db` |
| `FAISS_PATH` | `<DATABASE_ROOT>/vector_db/faiss_db` |
| `GRAPH_PATH` | `<DATABASE_ROOT>/graph_db/graph_store/graph_store.pkl` |
| `BM25_PATH` | `<DATABASE_ROOT>/keyword_db/bm25_store/bm25_store.pkl` |
| `KB_REGISTRY_PATH` | `<DATABASE_ROOT>/kb_registry.json` — read directly by the registry module; it appears in neither `config.py` nor `.env.example` |

**Server**

| Variable | Default |
|---|---|
| `VECTOR_BACKEND` | `chroma` (lower-cased; `chroma` or `faiss`) |
| `FRONTEND_URL` | `http://localhost:5173` — see [§10](#%EF%B8%8F-10-known-gaps) |
| `FLASK_DEBUG` | `true` |
| `PORT` | `5001` (`Backend/.env.example` sets `5000`) |

**Frontend**

| Variable | Default |
|---|---|
| `VUE_APP_API_URL` | `http://localhost:5000` in `Frontend/.env.example`; unset, the client falls back to an empty base URL and relies on the dev proxy |

**Not configurable by environment**

- **Maximum upload size:** 50 MB (`50 * 1024 * 1024`).
- **Allowed extensions:** `pdf`, `txt`, `md`, `docx`.
- **Web search results per query:** 5.
- **SSE drain timeout:** 180 seconds.

**Two things to know when you change a value**

- `RETRIEVAL_TOP_K`, `RERANK_TOP_K`, `MAX_CONTEXT_CHARS`, and the chunking pair are **re-read from the
  environment inside their own modules** rather than imported from the `Config` object. Setting them in
  `.env` works; monkey-patching `Config` at runtime does not.
- `Backend/.env.example` ships `OLLAMA_MODEL=llama3.2:latest`, while the code default is `llama3.2`.
  Whichever you use, be consistent — they are different model tags to Ollama.

</details>

<br>

---

<br>

## ⚠️ 10. KNOWN GAPS

Honest state of the repository as it stands. None of these block local development; all of them will
bite someone eventually.

- **There is no runnable production recipe.** `Backend/src/main.py` documents a
  `gunicorn -w 1 -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker …` command, but neither
  `gunicorn` nor `gevent-websocket` appears in `Backend/requirements.txt`. Copy that command into a
  fresh environment and it fails at the shell. Install both packages first, and keep the single-worker
  constraint — the SSE stream depends on it.
- **`npm run lint` does nothing useful.** The script is declared in `Frontend/package.json`, but
  `@vue/cli-plugin-eslint` is absent from both the dependencies and the lockfile, and there is no
  ESLint configuration file anywhere in the repository. The script fails when invoked.
- **`Frontend/documentation/README.md` describes a build that isn't there.** It refers to Vite,
  `npm run dev`, port 5173, `vite.config.js`, and an `index.html` at the package root. The real build is
  Vue CLI / webpack, `npm run serve`, port 8080, `vue.config.js`, and `public/index.html`.
- **The `FRONTEND_URL` default is wrong.** Both `Backend/src/config.py` and `Backend/.env.example` set
  it to `http://localhost:5173`, a port nothing in this project listens on. CORS still works only
  because the allowlist names `http://localhost:8080` explicitly as well.
- **The backend's default port disagrees with every document that names it.** `Backend/src/config.py`
  falls back to `5001`, while `Backend/.env.example`, `Backend/README.md`, and this file's own examples
  all use `5000`. Run `python src/main.py` without a `.env` and the API binds 5001 — at which point the
  frontend's dev proxy, which targets 5000, silently fails to reach it.
- **The vector store is committed to git.** `Backend/src/data/databases/vector_db/chroma_db/chroma.sqlite3`
  is tracked. `.gitignore` ignores `Backend/data/`, but `DATA_ROOT` resolves against the working
  directory — and the app starts inside `src/` — so the real data path is `Backend/src/data/` and the
  ignore rules never match it. Every ingest grows the repository.
- **There is no test harness.** No test framework in either manifest, no `tests/` directory, no CI
  configuration. Nothing in this README can be regression-checked automatically.
- **There is no licence.** No `LICENSE` file exists, so the terms for use, modification, and
  redistribution are formally undefined.

<br>

---

<br>

## 📚 11. DOCUMENTATION

Each half documents itself next to its own code.

| Document | What it covers |
|---|---|
| [`Backend/README.md`](Backend/README.md) | Backend quickstart |
| [`Backend/documentation/README.md`](Backend/documentation/README.md) | Index of the backend documentation set |
| [`Backend/documentation/rag-pipeline.md`](Backend/documentation/rag-pipeline.md) | Every pipeline node, the state machine, the retry loop, the retrieval stores |
| [`Backend/documentation/api.md`](Backend/documentation/api.md) | All eight HTTP endpoints with request and response shapes, plus an SSE reference — see the caveat in [§8](#-8-api) |
| [`Backend/documentation/architecture.md`](Backend/documentation/architecture.md) | Configuration reference, persistence, ingestion, and the events/SSE system |
| [`Frontend/README.md`](Frontend/README.md) | Frontend quickstart |
| [`Frontend/documentation/README.md`](Frontend/documentation/README.md) | Index of the frontend documentation set — see the caveat in [§10](#%EF%B8%8F-10-known-gaps) |
| [`Frontend/documentation/components.md`](Frontend/documentation/components.md) | Every component — props, emits, rendered output, behaviour |
| [`Frontend/documentation/state.md`](Frontend/documentation/state.md) | Pinia stores, the API service, SSE streaming, chat-history persistence |

Two files answer most configuration questions directly:
[`Backend/.env.example`](Backend/.env.example) for the backend and
[`Frontend/package.json`](Frontend/package.json) for the frontend's scripts and dependency versions.

<br>

---

<br>

## 🗺️ 12. ROADMAP

Where this goes next, in the order it makes sense to do it.

| # | Next step | What it unlocks |
|---|---|---|
| 1 | **Untrack the committed vector store** — `Backend/src/data/databases/vector_db/chroma_db/chroma.sqlite3` is under version control. `.gitignore` ignores `Backend/data/`, but the code resolves `DATA_ROOT` against the working directory, which is `src/`. | Stops a binary database growing in the history on every ingest, and makes the ignore rules match where data is actually written. |
| 2 | **Make linting real** — add `@vue/cli-plugin-eslint` and an ESLint configuration. | Turns the already-declared `lint` script into a working quality gate for the frontend. |
| 3 | **Stand up a test harness** — a framework for each half and a first suite over the pipeline nodes and the API. | Lets the pipeline's routing, retry, and fall-back paths be verified instead of reasoned about. |
| 4 | **Write the deployment story** — pin the production server packages, then document a repeatable deploy. | Gives the project a supported way to run outside a development machine. |

<br>
