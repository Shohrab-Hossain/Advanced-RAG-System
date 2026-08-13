# Mission

**adRAG** — "advanced RAG" — is a multi-stage Retrieval-Augmented Generation pipeline that produces
**grounded, cited answers from the user's own documents**, and makes every step of how it got there
visible while it runs.

The product name is `adRAG` (`Frontend/public/index.html` `<title>`,
`Frontend/src/pages/home/views/HomeView.vue:13` hero `<h1>`); the repository folder is
"Advanced RAG System". The app's own one-line description, from
`Frontend/public/index.html`:

> A multi-stage Retrieval-Augmented Generation pipeline combining hybrid search, cross-encoder reranking,
> and self-reflection to generate grounded, cited answers from your documents.

<br>

## The problem it solves

A plain RAG system does one similarity search and hands the top chunks to an LLM. That fails in three
ways this project attacks directly:

1. **One retrieval strategy misses.** Dense vector search misses exact keyword and identifier matches;
   keyword search misses paraphrase; neither follows entity relationships across chunks. adRAG runs
   **three retrievers at once** — dense vector, BM25 sparse, and an entity knowledge graph — and merges
   them (`Backend/src/rag_pipeline/retrieval/node.py`).
2. **Retrieval scores are not relevance.** Bi-encoder similarity ranks by embedding proximity, not by
   whether a passage answers *this* query. A cross-encoder reranker rescores every candidate against the
   query before anything reaches the LLM (`Backend/src/rag_pipeline/ranking/reranker.py`).
3. **The model will answer anyway.** Given weak context, an LLM produces a confident, unsupported answer.
   adRAG adds a **self-reflection agent** that judges whether every claim is traceable to the retrieved
   context, and either retries retrieval (escalating to web search when the knowledge base had nothing
   useful) or appends an explicit caveat to the answer
   (`Backend/src/rag_pipeline/generation/reflection.py`).

A fourth problem is about trust rather than accuracy: a RAG pipeline is a black box. adRAG streams a
typed event from every node over Server-Sent Events, so the UI shows the planner's decision, each store's
hit count, the reranker's scores, the compression ratio, the answer's confidence, and the grounding
verdict — as they happen.

<br>

## Who it is for

A single developer or researcher running the system **locally** against their own document set. There is
no sign-up, no user model, no tenancy: the app boots straight into a working state, and the frontend
talks to a Flask server on localhost — port `5001` by default (`config.py:68`), or whichever free port the
`dev.py` launcher picked. The `Ollama` provider path exists so the whole system can
run with **no data leaving the machine** — `Frontend/src/pages/configuration/views/ConfigView.vue:12`
states this as the provider's headline property ("Ollama runs entirely on your machine — no data sent
externally"), and repeats it at `:133`.

<br>

## Goals

- **Grounded over fluent.** Every claim in an answer should trace to a retrieved chunk; unsupported
  answers are marked, not hidden. The reflection prompt is deliberately strict: "if ANY claim cannot be
  verified from the context, set grounded=false".
- **Show the work.** The pipeline's internal state is a first-class part of the product, not debug output.
- **Recall through diversity.** Three retrieval strategies with different failure modes, merged and then
  rescored, rather than one strategy tuned harder.
- **Local-first, provider-optional.** Works with a local Ollama model or an OpenAI key; the choice is a
  runtime toggle, not a build-time one.
- **Zero-setup persistence.** Indexes survive a restart with no database server to install — Chroma's
  embedded persistent client plus two pickle files.

<br>

## Non-goals

These are visible in the code as things deliberately *not* built:

- **No authentication, users, or multi-tenancy.** No auth middleware exists anywhere in
  `Backend/src/app.py`. The index is a single global corpus shared by every request. Note that CORS is
  **not** a substitute boundary here: the origin allowlist at `app.py:44` ends with a literal `"*"`, so
  every origin is permitted — localhost binding is what actually contains this scope choice, and it stops
  containing it on the first deployment (see
  [`../security/trust-boundaries/README.md`](../security/trust-boundaries/README.md)).
- **No conversational memory.** Each query is an independent pipeline run. `RAGState` carries a single
  `query` string with no message history, and chat history in the frontend is a browser-local record of
  past results, not context fed back to the model.
- **No cloud deployment story.** There is no Dockerfile, no CI config, no infrastructure directory. The
  documented run modes are the Flask dev server and a single-worker gunicorn command noted in
  `Backend/src/main.py`.
- **No test suite.** No test files or test runner exist in the repository as of this writing.
- **No document-scoped querying.** Uploaded files are registered individually as "knowledge bases" and can
  be deleted individually, but a query always searches the entire index — there is no per-KB filter in the
  retrieval path.

<br>

## Success criteria

TODO: no measured accuracy target, benchmark, evaluation set, or latency budget is recorded anywhere in
the repository. Confirm with the owner what "good" means for this project before treating any of the
above as a bar.
