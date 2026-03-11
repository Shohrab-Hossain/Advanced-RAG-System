"""
Reasoning / Generation Agent Node
------------------------------------
Takes the compressed context and generates a structured answer
with inline citations [1], [2] referencing the source documents.

Output is a JSON object parsed by JsonOutputParser.
Falls back to a plain string generation if parsing fails.

Emits: stage_start → stage_complete | stage_error
"""

from langchain_core.prompts import ChatPromptTemplate

from ..state import RAGState
from ..core.events import emit
from ..encoding.llm import get_llm, safe_json_parse

_REASONING_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert reasoning and answer generation agent.

Generate a comprehensive, accurate answer to the user's query using ONLY the
provided context. Do not add information not present in the context.

Instructions:
1. Use inline citations like [1], [2] after each claim
2. Be specific — include exact facts, numbers, and names from the context
3. Structure longer answers with clear paragraphs
4. If the context is insufficient to fully answer, explicitly say so

Respond ONLY with valid JSON (no markdown fences):
{{
  "answer": "<detailed answer with [citations]>",
  "confidence": <0.0-1.0 float>,
  "cited_sources": [<list of cited source indices, 1-based>],
  "key_facts": ["<fact1>", "<fact2>"],
  "is_sufficient": <bool>
}}"""),
    ("human", "Query: {query}\n\nContext:\n{context}"),
])


def reasoning_node(state: RAGState) -> dict:
    session_id = state.get("session_id")
    query = state["query"]
    compressed_context = state.get("compressed_context", "")
    context_docs = state.get("context", [])
    provider = state.get("provider", "openai")
    ollama_model = state.get("ollama_model")

    emit(session_id, "stage_start", {
        "stage": "reasoning",
        "message": "Generating answer from retrieved evidence...",
    })

    sources = []
    for i, doc in enumerate(context_docs):
        meta = doc.get("metadata", {})
        sources.append({
            "index": i + 1,
            "file_name": meta.get("file_name") or meta.get("title") or "Unknown",
            "source_type": doc.get("source", "unknown"),
            "url": meta.get("url", ""),
            "page": meta.get("page", ""),
            "rerank_score": round(doc.get("rerank_score", doc.get("score", 0.0)), 4),
            # include both preview and full content for frontend expansion
            "content_preview": doc["content"][:250],
            "content": doc["content"],
        })

    context_text = compressed_context or "\n\n".join(d["content"] for d in context_docs)

    if not context_text.strip():
        llm = get_llm(provider, model=ollama_model)
        result = llm.invoke(
            f"Answer this question directly (no documents available): {query}"
        )
        emit(session_id, "stage_complete", {
            "stage": "reasoning",
            "confidence": 0.5,
            "message": "Direct answer (no retrieved context)",
        })
        return {"answer": result.content, "sources": []}

    try:
        llm = get_llm(provider, json_mode=True, model=ollama_model)
        raw = (_REASONING_PROMPT | llm).invoke({"query": query, "context": context_text})
        result = safe_json_parse(raw.content)

        answer = result.get("answer", "No answer generated.")
        confidence = float(result.get("confidence", 0.5))

        # Filter to only sources actually cited in the answer.
        # If the LLM cited nothing (answered from training knowledge), return no sources.
        cited_indices = set(result.get("cited_sources", []))
        cited_sources = [s for s in sources if s["index"] in cited_indices]

        emit(session_id, "stage_complete", {
            "stage": "reasoning",
            "confidence": round(confidence, 2),
            "is_sufficient": result.get("is_sufficient", True),
            "key_facts": result.get("key_facts", []),
            "message": f"Answer generated ({confidence:.0%} confidence)",
        })
        return {"answer": answer, "sources": cited_sources}

    except Exception as e:
        emit(session_id, "stage_error", {"stage": "reasoning", "error": str(e)})
        try:
            llm = get_llm(provider, model=ollama_model)
            prompt = f"Context:\n{context_text[:3000]}\n\nQuestion: {query}\n\nAnswer:"
            result = llm.invoke(prompt)
            return {"answer": result.content, "sources": sources}
        except Exception:
            return {"answer": "Unable to generate an answer.", "sources": sources}
