# Tech stack

Every runtime dependency, its version floor as pinned in the repository, and the job it does. "Why"
entries state the role the code actually gives the dependency; where the *choice* between alternatives is
load-bearing, the reasoning is recorded as an ADR in [`../../decisions/ADRs/`](../../decisions/ADRs/INDEX.md).

<br>

## Backend — Python

Pinned in `Backend/requirements.txt`. No Python version floor is declared anywhere in the repository
(no `pyproject.toml`, `setup.py`, or `python_requires`); the code uses `str | None` union syntax and
`dict[str, queue.Queue]` builtin generics, which require **Python 3.10+**.

| Package | Floor | Why it is here |
|---|---|---|
| `flask` | `>=3.0.0` | The HTTP server. Seven REST routes plus the SSE streaming route (eight in all), under `/api/*`. |
| `flask-cors` | `>=4.0.0` | Allows the Vue dev server origin to call the API cross-origin; scoped to `r"/api/*"` (`app.py:43`). The origin list (`app.py:44`) is *meant* to be explicit but currently ends in a literal `"*"`, which permits every origin — see [`../security/trust-boundaries/README.md`](../security/trust-boundaries/README.md). |
| `python-dotenv` | `>=1.0.0` | Loads `Backend/.env` at import time in `config.py`; all configuration is environment-driven. |
| `langgraph` | `>=0.1.0` | The pipeline is a compiled `StateGraph`, not a call chain. Chosen because the flow is not linear — the planner branches three ways and reflection loops backwards; conditional edges express that directly. |
| `langchain` | `>=0.2.0` | Core abstractions the nodes build on. |
| `langchain-text-splitters` | `>=0.2.0` | `RecursiveCharacterTextSplitter` for chunking. |
| `langchain-openai` | `>=0.1.0` | `ChatOpenAI` — the OpenAI provider. |
| `langchain-ollama` | `>=0.1.0` | `ChatOllama` — the local provider, including `format="json"` for constrained JSON output. |
| `langchain-community` | `>=0.2.0` | The document loaders: `PyPDFLoader`, `TextLoader`, `Docx2txtLoader`, `UnstructuredMarkdownLoader`. |
| `chromadb` | `>=0.5.0` | Default dense vector store, via `PersistentClient` — an embedded, file-backed index needing no separate server, which is what makes the local-first setup zero-install. |
| `faiss-cpu` | `>=1.7.4` | Optional alternative vector backend, active only when `VECTOR_BACKEND=faiss`. Imported lazily; the module raises a clear `RuntimeError` if it is missing when selected. |
| `sentence-transformers` | `>=3.0.0` | Two distinct jobs: the `SentenceTransformer` bi-encoder that produces chunk/query embeddings, and the `CrossEncoder` that reranks. Both models download on first run. |
| `rank-bm25` | `>=0.2.2` | `BM25Okapi` sparse scoring — the keyword half of hybrid retrieval, catching exact terms embeddings miss. |
| `networkx` | `>=3.3` | The in-memory entity graph for GraphRAG. An undirected `nx.Graph` of document and entity nodes; traversal is plain neighbour iteration, so no graph database is needed. |
| `pypdf` | `>=4.0.0` | PDF text extraction (used by `PyPDFLoader`). |
| `docx2txt` | `>=0.8` | DOCX text extraction. |
| `unstructured` | `>=0.14.0` | Markdown parsing (used by `UnstructuredMarkdownLoader`). |
| `ddgs` | `>=7.0.0` | DuckDuckGo search for the external-tools node — no API key required, which keeps the optional web path zero-config. The node imports `ddgs` first and falls back to the legacy `duckduckgo_search` package name. |
| `numpy` | `>=1.26.0` | Array handling, notably for the FAISS path. |
| `requests` | `>=2.31.0` | Probing the Ollama server (`GET {base}/api/tags`). The docstring in `encoding/llm.py` notes it is used instead of `urllib` because it is "more reliable on Windows". |

**Model defaults** (env-overridable, from `Backend/src/config.py`):

| Role | Default model |
|---|---|
| Embeddings | `all-MiniLM-L6-v2` |
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| OpenAI LLM | `gpt-4o-mini` |
| Ollama LLM | `llama3.2` (`.env.example` suggests `llama3.2:latest`) |

<br>

## Frontend — JavaScript

Pinned in `Frontend/package.json` (`name: rag-frontend`, `version: 1.0.0`, `private: true`).

| Package | Version | Why it is here |
|---|---|---|
| `vue` | `^3.4.0` | The UI framework. Every component is `<script setup>` Composition API. |
| `vue-router` | `^4.6.4` | Four routes in HTML5 history mode, all lazily imported. |
| `pinia` | `^2.1.7` | State management. Two setup-style stores: `rag` (everything about documents, queries, and results) and `ui` (theme + modal). |
| `axios` | `^1.7.0` | REST calls. Used for upload specifically because its `onUploadProgress` callback drives the transfer progress bar — `fetch` cannot report upload progress. |
| `marked` | `^12.0.0` | Renders the LLM's markdown answer to HTML in `ResultDisplay.vue`. |
| `tailwindcss` | `^3.4.0` (dev) | All styling. `darkMode: 'class'`, with a custom `warm` stone-tinted palette and component classes in `src/assets/main.css`. |
| `postcss` + `autoprefixer` | `^8.4.0` / `^10.4.0` (dev) | Tailwind's build pipeline. |
| `@vue/cli-service` + `@vue/cli-plugin-babel` | `^5.0.8` (dev) | The webpack-based build and dev server. The dev server proxies `/api` to `process.env.DEV_API_TARGET \|\| 'http://localhost:5000'` (`vue.config.js:12`), so the target follows the port `dev.py` chose. Note `@vue/cli-plugin-eslint` is **not** installed, so the `lint` script does not run. |

**Fonts** are loaded from Google Fonts in `Frontend/public/index.html`: `Plus Jakarta Sans`
(400/500/600/700) for `font-sans` and `JetBrains Mono` (400/500) for `font-mono`.

<br>

## Notably absent

No test framework, no linter config beyond the `vue-cli-service lint` script, no TypeScript, no
Dockerfile, no CI configuration, and no database server. Adding any of these is a new decision, not a
restoration of something that was removed.
