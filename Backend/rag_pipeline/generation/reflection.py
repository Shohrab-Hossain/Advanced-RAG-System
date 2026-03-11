"""
Self-Reflection Agent Node
----------------------------
Critically evaluates the generated answer against the retrieved context.
If the answer contains unsupported claims AND retry budget remains,
it signals the graph to loop back to retrieval with augmented context.

On the final pass (grounded or budget exhausted), it produces the
final_answer with an optional caveat and populates pipeline_metadata.

Emits: stage_start → stage_complete | retry | finalize | stage_error
"""

import os
from langchain_core.prompts import ChatPromptTemplate

from ..state import RAGState
from ..core.events import emit
from ..encoding.llm import get_llm, safe_json_parse

MAX_RETRIES = int(os.getenv("MAX_REFLECTION_RETRIES", "2"))

_REFLECTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a strict grounding verification agent for a RAG system.

Evaluate whether the generated answer is fully supported by the provided context.

Criteria:
1. Every factual claim must be traceable to the context
2. No hallucinated numbers, names, or events
3. Citations ([1], [2]) must reference content that actually supports the claim

Respond ONLY with valid JSON:
{{
  "grounded": <bool>,
  "confidence": <0.0-1.0>,
  "issues": ["<issue1>", "<issue2>"],
  "feedback": "<specific feedback for improvement>",
  "should_retry": <bool>
}}

Be strict: if ANY claim cannot be verified from the context, set grounded=false."""),
    ("human", """Query: {query}

Context used:
{context}

Generated Answer:
{answer}"""),
])


def reflection_node(state: RAGState) -> dict:
    session_id = state.get("session_id")
    query = state["query"]
    answer = state.get("answer", "")
    context_docs = state.get("context", [])
    retry_count = state.get("retry_count", 0)
    provider = state.get("provider", "openai")
    ollama_model = state.get("ollama_model")

    emit(session_id, "stage_start", {
        "stage": "reflection",
        "message": "Verifying answer grounding and citations...",
        "attempt": retry_count + 1,
        "max_attempts": MAX_RETRIES + 1,
    })

    if not answer:
        return {
            "grounded": False,
            "reflection_feedback": "No answer to verify",
            "retry_count": retry_count,
        }

    context_text = (
        "\n\n".join(d["content"] for d in context_docs)
        if context_docs else "No context was retrieved."
    )

    try:
        llm = get_llm(provider, json_mode=True, model=ollama_model)
        raw = (_REFLECTION_PROMPT | llm).invoke({
            "query": query,
            "context": context_text[:4000],
            "answer": answer,
        })
        result = safe_json_parse(raw.content)

        grounded: bool = bool(result.get("grounded", True))
        confidence: float = float(result.get("confidence", 0.8))
        feedback: str = result.get("feedback", "")
        issues: list = result.get("issues", [])
        raw_retry: bool = bool(result.get("should_retry", False))

        # Decide if we actually retry
        will_retry = (not grounded) and raw_retry and (retry_count < MAX_RETRIES)

        # Detect weak KB context: no docs or all cross-encoder scores below 0
        # (ms-marco cross-encoder returns negative logits for irrelevant pairs)
        max_rerank = max((d.get("rerank_score", 0) for d in context_docs), default=None)
        kb_insufficient = len(context_docs) == 0 or (max_rerank is not None and max_rerank < 0)
        # Escalate to web search on first retry when KB had nothing useful
        escalate_external = will_retry and kb_insufficient and not state.get("use_external", False)

        emit(session_id, "stage_complete", {
            "stage": "reflection",
            "grounded": grounded,
            "confidence": round(confidence, 2),
            "issues": issues,
            "will_retry": will_retry,
            "escalate_external": escalate_external,
            "message": (
                f"{'✓ Grounded' if grounded else '✗ Not grounded'} "
                f"| Confidence {confidence:.0%}"
                + (f" — retrying with web search ({retry_count + 2}/{MAX_RETRIES + 1})"
                   if escalate_external
                   else f" — retrying ({retry_count + 2}/{MAX_RETRIES + 1})"
                   if will_retry else "")
            ),
        })

        if will_retry:
            msg = (
                f"KB had no relevant content — escalating to web search: {feedback[:100]}"
                if escalate_external
                else f"Re-running retrieval with feedback: {feedback[:120]}"
            )
            emit(session_id, "retry", {
                "attempt": retry_count + 2,
                "max_attempts": MAX_RETRIES + 1,
                "reason": feedback,
                "escalate_external": escalate_external,
                "message": msg,
            })
            return {
                "grounded": grounded,
                "reflection_feedback": feedback,
                "retry_count": retry_count + 1,
                **({"use_external": True} if escalate_external else {}),
            }

        # ── Final output ──────────────────────────────────────────────────────
        caveat = (
            "\n\n⚠️ *Some claims may not be fully supported by the retrieved documents.*"
            if not grounded else ""
        )
        final_answer = answer + caveat

        emit(session_id, "finalize", {
            "stage": "reflection",
            "grounded": grounded,
            "message": "Pipeline complete — producing final answer",
        })

        return {
            "grounded": grounded,
            "reflection_feedback": feedback,
            "retry_count": retry_count,
            "final_answer": final_answer,
            "final_sources": state.get("sources", []),
            "pipeline_metadata": {
                "query_type": state.get("query_type", "factual"),
                "sources_used": [d.get("source") for d in context_docs],
                "retry_count": retry_count,
                "grounded": grounded,
                "confidence": round(confidence, 2),
                "issues": issues,
            },
        }

    except Exception as e:
        emit(session_id, "stage_error", {"stage": "reflection", "error": str(e)})
        return {
            "grounded": True,
            "reflection_feedback": "",
            "retry_count": retry_count,
            "final_answer": answer,
            "final_sources": state.get("sources", []),
            "pipeline_metadata": {"error": str(e)},
        }
