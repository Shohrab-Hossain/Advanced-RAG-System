"""
Health Check Routes
-------------------
GET /api/health — liveness only.

Deliberately shallow: infra/dev.py polls this while the embedding and reranker
models are still loading, so it must answer before the pipeline is usable.
"""

from flask import Blueprint, jsonify

health_check_bp = Blueprint("health_check", __name__)


# ── Routes ────────────────────────────────────────────────────────────────────

@health_check_bp.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"})
