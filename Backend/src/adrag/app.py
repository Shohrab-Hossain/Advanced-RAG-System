"""
Flask Application — RAG API
---------------------------
The application factory. Every route lives in routes/<resource>/ as a Blueprint;
this file wires them together and owns nothing else.

Endpoints:
  POST   /api/query                        → SSE stream of pipeline events + final answer
  POST   /api/upload                       → upload & index a document
  GET    /api/documents                    → stats on indexed content
  DELETE /api/clear                        → wipe all indexed documents
  GET    /api/knowledge-bases              → list uploaded knowledge bases
  DELETE /api/knowledge-bases/<file_hash>  → remove one knowledge base
  GET    /api/providers                    → available LLM providers
  GET    /api/health                       → health check

Run it with `adrag-dev`, `python -m adrag.main`, or gunicorn against `adrag.app:app`
— see main.py. One worker only: the SSE session queues are process memory and every
store is a module singleton, so forking splits the producer from its consumer.
"""

import os

from flask import Flask
from flask_cors import CORS

from adrag.config import Config
from adrag.routes import BLUEPRINTS


# ── App factory ───────────────────────────────────────────────────────────────

def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": [Config.FRONTEND_URL, "http://localhost:3000", "http://localhost:5000", "http://localhost:8080", "http://localhost:8081", "*"],
                "methods": ["GET", "POST", "DELETE", "OPTIONS"],
                "allow_headers": ["Content-Type"],
                "expose_headers": ["Content-Type"],
            }
        },
    )

    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

    for blueprint in BLUEPRINTS:
        app.register_blueprint(blueprint)

    return app


# ── Module-level app ──────────────────────────────────────────────────────────
# Imported by main.py and named directly by the gunicorn command (adrag.app:app).
# There is deliberately no __main__ block here — main.py is the one entry point.

app = create_app()
