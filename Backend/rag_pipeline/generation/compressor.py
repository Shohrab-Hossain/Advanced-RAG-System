"""
Context Compression Node
--------------------------
If the concatenated top-k documents exceed MAX_CONTEXT_CHARS, an LLM
is used to extract and compress only the query-relevant passages.

This keeps the reasoning prompt short and focused, improving answer
quality and reducing cost.

Emits: stage_start → stage_complete | stage_error
"""

import os
from langchain_core.prompts import ChatPromptTemplate

from ..state import RAGState
from ..core.events import emit
from ..encoding.llm import get_llm

MAX_CONTEXT_CHARS = int(os.getenv("MAX_CONTEXT_CHARS", "4000"))

_COMPRESS_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a context compression expert.
Given a query and multiple source passages, extract and compress ONLY the information
that is directly relevant to answering the query.

Rules:
- Preserve key facts, numbers, names, dates, and relationships
- Remove off-topic, redundant, or background-only content
- Output a single coherent compressed passage (not bullet points)
- Maximum {max_chars} characters
- Keep source references like [1], [2] if present"""),
    ("human", "Query: {query}\n\nDocuments:\n{documents}"),
])


def compressor_node(state: RAGState) -> dict:
    session_id = state.get("session_id")
    query = state["query"]
    context = state.get("context", [])
    provider = state.get("provider", "openai")

    emit(session_id, "stage_start", {
        "stage": "compressor",
        "message": "Compressing context to fit LLM window...",
    })

    if not context:
        emit(session_id, "stage_complete", {
            "stage": "compressor",
            "message": "No context to compress",
        })
        return {"compressed_context": ""}

    doc_blocks = []
    for i, doc in enumerate(context):
        meta = doc.get("metadata", {})
        label = meta.get("file_name") or meta.get("title") or doc.get("source", f"Source {i+1}")
        doc_blocks.append(f"[{i+1}] {label}\n{doc['content']}")
    full_text = "\n\n---\n\n".join(doc_blocks)

    original_len = len(full_text)

    if original_len <= MAX_CONTEXT_CHARS:
        emit(session_id, "stage_complete", {
            "stage": "compressor",
            "original_chars": original_len,
            "compressed_chars": original_len,
            "message": f"Context already within limit ({original_len} chars)",
        })
        return {"compressed_context": full_text}

    try:
        llm = get_llm(provider)
        chain = _COMPRESS_PROMPT | llm
        result = chain.invoke({
            "query": query,
            "documents": full_text[:10_000],
            "max_chars": MAX_CONTEXT_CHARS,
        })
        compressed = result.content

        emit(session_id, "stage_complete", {
            "stage": "compressor",
            "original_chars": original_len,
            "compressed_chars": len(compressed),
            "ratio": round(len(compressed) / original_len, 2),
            "message": f"Compressed {original_len:,} → {len(compressed):,} chars",
        })
        return {"compressed_context": compressed}

    except Exception as e:
        emit(session_id, "stage_error", {"stage": "compressor", "error": str(e)})
        return {"compressed_context": full_text[:MAX_CONTEXT_CHARS]}
