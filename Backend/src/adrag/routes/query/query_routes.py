"""
Query Routes
------------
POST /api/query — run the LangGraph pipeline and stream its progress as SSE.

The pipeline runs on a daemon thread; this route only frames its events as HTTP.
Errors are IN-BAND: a pipeline failure is a 200 carrying an `error` event, not an
HTTP error status, because the stream has already begun by the time one can occur.
"""

import uuid
import threading

from flask import Blueprint, request, Response, jsonify

from adrag.config import Config
from adrag.custom_packages.rag_pipeline.workflow import rag_graph
from adrag.custom_packages.rag_pipeline.events import (
    create_session,
    close_session,
    format_sse,
)

query_bp = Blueprint("query", __name__)

# A disconnected browser frees the socket, never the compute — the daemon thread
# runs to completion regardless. This is the only bound on a wedged pipeline.
_EVENT_TIMEOUT_SECONDS = 180


# ── Routes ────────────────────────────────────────────────────────────────────

@query_bp.route("/api/query", methods=["POST"])
def query():
    """
    Accept a JSON body {"query": "...", "provider": "openai"|"ollama"} and stream SSE events.
    Each event:  data: {"type": "<event_type>", "data": {...}}\n\n
    Final event: data: {"type": "done", "data": {"answer":..., "sources":...}}\n\n
    """
    body = request.get_json(silent=True)
    if not body or not body.get("query", "").strip():
        return jsonify({"error": "Missing or empty 'query' field"}), 400

    provider = body.get("provider", Config.DEFAULT_PROVIDER).lower().strip()
    if provider not in ("openai", "ollama"):
        return jsonify({"error": "provider must be 'openai' or 'ollama'"}), 400

    # Optional model override (only meaningful for Ollama; ignored for OpenAI)
    ollama_model = body.get("model") or None

    session_id = str(uuid.uuid4())
    _, event_queue = create_session(session_id)

    initial_state = {
        "query": body["query"].strip(),
        "session_id": session_id,
        "provider": provider,
        "ollama_model": ollama_model,
        # Planner will overwrite these:
        "retrieve": True,
        "use_external": False,
        "query_type": "factual",
        # Empty doc lists (filled by retrieval nodes):
        "vector_docs": [],
        "bm25_docs": [],
        "graph_docs": [],
        "web_docs": [],
        "all_docs": [],
        "context": [],
        "compressed_context": "",
        "answer": "",
        "sources": [],
        "grounded": True,
        "reflection_feedback": "",
        "retry_count": 0,
        "final_answer": "",
        "final_sources": [],
        "pipeline_metadata": {},
    }

    def _run():
        try:
            result = rag_graph.invoke(initial_state)
            event_queue.put({
                "type": "done",
                "data": {
                    "answer": result.get("final_answer") or result.get("answer", ""),
                    "sources": result.get("final_sources") or result.get("sources", []),
                    "metadata": result.get("pipeline_metadata", {}),
                },
            })
        except Exception as exc:
            event_queue.put({
                "type": "error",
                "data": {"message": str(exc), "stage": "pipeline"},
            })
        finally:
            event_queue.put(None)   # sentinel → close stream

    threading.Thread(target=_run, daemon=True).start()

    def _generate():
        try:
            while True:
                item = event_queue.get(timeout=_EVENT_TIMEOUT_SECONDS)
                if item is None:
                    yield format_sse({"type": "stream_end"})
                    break
                yield format_sse(item)
        except Exception:
            yield format_sse({"type": "error", "data": {"message": "Stream timeout"}})
        finally:
            close_session(session_id)

    return Response(
        _generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
