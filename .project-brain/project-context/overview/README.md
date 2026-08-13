# 📖 Overview

What adRAG is, who it is for, what it deliberately is not, and what it is built out of. Read this area
first — the rest of `project-context/` assumes its vocabulary.

<br>

---

<br>

## Index

| Doc | Holds |
|---|---|
| [`mission.md`](mission.md) | The problem, the users, the value, the explicit non-goals, and how success is judged |
| [`glossary.md`](glossary.md) | Domain vocabulary — Self-RAG, hybrid retrieval, GraphRAG, reranking, grounding, and the project's own terms |
| [`tech-stack.md`](tech-stack.md) | Every runtime dependency on both sides, with the reason it is there and the version floor |

<br>

---

<br>

## The 30-second version

adRAG turns a pile of the user's own documents into a question-answering system that shows its work.
Answers carry inline `[1]`-style citations back to the exact chunks that support them, a self-reflection
pass flags anything it cannot verify, and the UI renders all eight pipeline stages live while the query
runs. It is a local-first, single-user system — no accounts, no multi-tenancy, no cloud dependency beyond
an optional OpenAI key.
