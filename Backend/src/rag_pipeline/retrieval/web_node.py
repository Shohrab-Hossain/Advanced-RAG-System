"""
External Tools Node — Web Search
----------------------------------
Called when the planner decides the knowledge base is insufficient
(e.g. recent events, live data) or when reflection escalates after
finding the KB had no relevant content.

Uses DuckDuckGo Search (no API key required).
Falls back gracefully if the library is unavailable.

Emits: stage_start → stage_complete | stage_skip | stage_error
"""

from ..state import RAGState
from ..core.events import emit

WEB_RESULTS = 5


def external_tools_node(state: RAGState) -> dict:
    session_id = state.get("session_id")
    query = state["query"]

    if not state.get("use_external", False):
        emit(session_id, "stage_skip", {
            "stage": "external_tools",
            "message": "Web search not needed",
        })
        return {"web_docs": []}

    emit(session_id, "stage_start", {
        "stage": "external_tools",
        "message": f"Searching the web for: {query[:60]}...",
    })

    try:
        try:
            from ddgs import DDGS          # new package name (>=7.0)
        except ImportError:
            from duckduckgo_search import DDGS  # legacy fallback

        web_docs = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=WEB_RESULTS):
                web_docs.append({
                    "content": f"{r.get('title', '')}\n\n{r.get('body', '')}",
                    "metadata": {
                        "url": r.get("href", ""),
                        "title": r.get("title", ""),
                        "source_type": "web",
                        "file_name": r.get("href", "Web"),
                    },
                    "score": 0.7,
                    "source": "web",
                    "rerank_score": 0.0,
                })
                print(f"Retrieved web doc: {r.get('title', '')} ({r.get('href', '')})")

        emit(session_id, "stage_complete", {
            "stage": "external_tools",
            "web_count": len(web_docs),
            "message": f"Found {len(web_docs)} web results",
        })
        return {"web_docs": web_docs}

    except ImportError:
        emit(session_id, "stage_error", {
            "stage": "external_tools",
            "error": "duckduckgo-search not installed",
        })
        return {"web_docs": []}

    except Exception as e:
        emit(session_id, "stage_error", {"stage": "external_tools", "error": str(e)})
        return {"web_docs": []}
