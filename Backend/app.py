"""
Flask Application — RAG API
-----------------------------
Endpoints:
  POST   /api/query      → SSE stream of pipeline events + final answer
  POST   /api/upload     → Upload & index a document
  GET    /api/documents  → Stats on indexed content
  DELETE /api/clear      → Wipe all indexed documents
  GET    /api/health     → Health check

The /api/query endpoint runs the LangGraph pipeline in a background thread
and streams Server-Sent Events (SSE) to the client in real time.
"""

import os
import uuid
import threading

from flask import Flask, request, Response, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename

from config import Config
from rag_pipeline.graph import rag_graph
from rag_pipeline.core.events import create_session, close_session, format_sse
from rag_pipeline.encoding.llm import check_ollama
from rag_pipeline.retrieval.vector import vector_store
from rag_pipeline.retrieval.bm25 import bm25_store
from rag_pipeline.retrieval.graph import graph_store
from rag_pipeline.ingestion.loader import load_file, generate_chunk_ids
from rag_pipeline.ingestion import registry as kb_registry


# ── App factory ───────────────────────────────────────────────────────────────

def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": [Config.FRONTEND_URL, "http://localhost:3000", "http://localhost:8080"],
                "methods": ["GET", "POST", "DELETE", "OPTIONS"],
                "allow_headers": ["Content-Type"],
                "expose_headers": ["Content-Type"],
            }
        },
    )

    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

    # ── Helper ─────────────────────────────────────────────────────────────────

    def _allowed(filename: str) -> bool:
        return (
            "." in filename
            and filename.rsplit(".", 1)[1].lower() in Config.ALLOWED_EXTENSIONS
        )

    # ── Routes ─────────────────────────────────────────────────────────────────

    @app.route("/api/query", methods=["POST"])
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

        session_id = str(uuid.uuid4())
        _, event_queue = create_session(session_id)

        initial_state = {
            "query": body["query"].strip(),
            "session_id": session_id,
            "provider": provider,
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
                    item = event_queue.get(timeout=180)   # 3-min hard timeout
                    if item is None:
                        yield "data: {\"type\": \"stream_end\"}\n\n"
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

    # ──────────────────────────────────────────────────────────────────────────

    @app.route("/api/upload", methods=["POST"])
    def upload():
        """Upload a document, chunk it, and index it into all three stores."""
        if "file" not in request.files:
            return jsonify({"error": "No file field in request"}), 400

        f = request.files["file"]
        if not f.filename:
            return jsonify({"error": "Empty filename"}), 400
        if not _allowed(f.filename):
            return jsonify({
                "error": f"Unsupported file type. Allowed: {', '.join(Config.ALLOWED_EXTENSIONS)}"
            }), 400

        filename = secure_filename(f.filename)
        file_path = os.path.join(Config.UPLOAD_FOLDER, filename)
        f.save(file_path)

        try:
            texts, metadatas = load_file(file_path)
            if not texts:
                return jsonify({"error": "No text could be extracted from this file"}), 422

            file_hash = metadatas[0].get("file_hash", str(uuid.uuid4()))
            chunk_ids = generate_chunk_ids(file_hash, len(texts))

            # Index into all three stores
            vector_store.add_documents(texts, metadatas, chunk_ids)
            bm25_store.add_documents(texts, metadatas)
            for i, (text, meta) in enumerate(zip(texts, metadatas)):
                graph_store.add_document(chunk_ids[i], text, meta)

            graph_stats = graph_store.get_stats()
            kb_entry = kb_registry.register(file_hash, filename, {
                "chunks": len(texts),
                "vectors": len(texts),   # 1 chunk → 1 embedding
                "entities": graph_store.count_entities_by_file(file_hash),
                "edges": graph_stats.get("edges", 0),
            })

            return jsonify({
                "success": True,
                "file_name": filename,
                "file_hash": file_hash,
                "chunks_indexed": len(texts),
                "kb": kb_entry,
                "stats": {
                    "vector_total": vector_store.count(),
                    "bm25_total": bm25_store.count(),
                    "graph": graph_stats,
                },
            })

        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    # ──────────────────────────────────────────────────────────────────────────

    @app.route("/api/documents", methods=["GET"])
    def documents():
        """Return current index statistics."""
        return jsonify({
            "vector_count": vector_store.count(),
            "bm25_count": bm25_store.count(),
            "graph": graph_store.get_stats(),
        })

    @app.route("/api/clear", methods=["DELETE"])
    def clear():
        """Wipe all indexed documents from all stores."""
        vector_store.clear()
        bm25_store.clear()
        graph_store.clear()
        kb_registry.clear_all()
        return jsonify({"success": True, "message": "All documents cleared"})

    @app.route("/api/knowledge-bases", methods=["GET"])
    def list_knowledge_bases():
        """Return all uploaded knowledge bases with per-KB stats."""
        return jsonify({"knowledge_bases": kb_registry.list_all()})

    @app.route("/api/knowledge-bases/<file_hash>", methods=["DELETE"])
    def delete_knowledge_base(file_hash):
        """Remove a specific knowledge base from all stores."""
        vector_store.delete_by_file(file_hash)
        bm25_store.delete_by_file(file_hash)
        graph_store.delete_by_file(file_hash)
        kb_registry.remove(file_hash)
        return jsonify({
            "success": True,
            "stats": {
                "vector_total": vector_store.count(),
                "bm25_total": bm25_store.count(),
                "graph": graph_store.get_stats(),
            },
        })

    @app.route("/api/providers", methods=["GET"])
    def providers():
        """Return available LLM providers and their status."""
        ollama_status = check_ollama()
        return jsonify({
            "providers": [
                {
                    "id": "openai",
                    "label": "OpenAI",
                    "model": Config.LLM_MODEL,
                    "available": bool(Config.OPENAI_API_KEY),
                },
                {
                    "id": "ollama",
                    "label": "Local (Ollama)",
                    "model": Config.OLLAMA_MODEL,
                    "base_url": Config.OLLAMA_BASE_URL,
                    "available": ollama_status["available"],
                    "models": ollama_status.get("models", []),
                },
            ],
            "default": Config.DEFAULT_PROVIDER,
        })

    @app.route("/api/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok", "version": "1.0.0"})

    return app


# ── Entry point ───────────────────────────────────────────────────────────────

app = create_app()

if __name__ == "__main__":
    app.run(
        debug=Config.DEBUG,
        host="0.0.0.0",
        port=Config.PORT,
        threaded=True,
    )
