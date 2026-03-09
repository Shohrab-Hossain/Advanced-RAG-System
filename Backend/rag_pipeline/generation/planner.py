"""
Planner Node — Self-RAG Decision
----------------------------------
Reads the user query and decides:
  • retrieve      — should we query the knowledge base?
  • use_external  — should we also run a web search?
  • query_type    — "factual" | "analytical" | "conversational"

Emits: stage_start → stage_complete (or stage_error on failure)
"""

from langchain_core.prompts import ChatPromptTemplate

from ..state import RAGState
from ..core.events import emit
from ..encoding.llm import get_llm, safe_json_parse

_PLANNER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a Self-RAG planning agent.
Analyze the user query and output a JSON decision object.

Rules:
- retrieve=true  → query requires domain knowledge / documents
- retrieve=false → simple math, greetings, pure coding questions
- use_external=true → query involves recent events, live data, or breaking news
- query_type: one of "factual", "analytical", "conversational"

Respond ONLY with valid JSON — no markdown, no extra text:
{{
  "retrieve": <bool>,
  "use_external": <bool>,
  "query_type": "<factual|analytical|conversational>",
  "reasoning": "<one sentence>"
}}"""),
    ("human", "Query: {query}"),
])


def planner_node(state: RAGState) -> dict:
    session_id = state.get("session_id")
    query = state["query"]
    provider = state.get("provider", "openai")

    emit(session_id, "stage_start", {
        "stage": "planner",
        "message": "Analyzing query — deciding retrieval strategy...",
    })

    try:
        llm = get_llm(provider, json_mode=True)
        raw = (_PLANNER_PROMPT | llm).invoke({"query": query})
        result: dict = safe_json_parse(raw.content)

        retrieve = bool(result.get("retrieve", True))
        use_external = bool(result.get("use_external", False))
        query_type = result.get("query_type", "factual")

        emit(session_id, "stage_complete", {
            "stage": "planner",
            "retrieve": retrieve,
            "use_external": use_external,
            "query_type": query_type,
            "reasoning": result.get("reasoning", ""),
            "message": (
                f"{'Retrieval needed' if retrieve else 'Direct answer'}"
                f"{' + web search' if use_external else ''}"
                f" | Type: {query_type}"
            ),
        })

        return {
            "retrieve": retrieve,
            "use_external": use_external,
            "query_type": query_type,
        }

    except Exception as e:
        emit(session_id, "stage_error", {"stage": "planner", "error": str(e)})
        return {"retrieve": True, "use_external": False, "query_type": "factual"}
