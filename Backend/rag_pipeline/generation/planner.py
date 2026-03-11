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

Rules for `retrieve`:
- true  → question is likely about user-uploaded domain documents (company reports, research papers, personal files, etc.)
- false → general world knowledge (history, science, geography, famous people, events), math, greetings, coding questions

Rules for `use_external`:
- true  → question involves recent events (last 1-2 years), live data, current news, or breaking information
- false → everything else (historical facts, stable knowledge, document-based questions)

Examples:
- "Who was the first person on the moon?" → retrieve=false, use_external=false (well-known historical fact)
- "What does the attached report say about revenue?" → retrieve=true, use_external=false (domain document)
- "What happened in the stock market today?" → retrieve=false, use_external=true (live data)
- "Summarize the uploaded PDF" → retrieve=true, use_external=false

query_type: one of "factual", "analytical", "conversational"

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
    ollama_model = state.get("ollama_model")

    emit(session_id, "stage_start", {
        "stage": "planner",
        "message": "Analyzing query — deciding retrieval strategy...",
    })

    try:
        llm = get_llm(provider, json_mode=True, model=ollama_model)
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
