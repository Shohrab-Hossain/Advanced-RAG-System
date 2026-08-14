"""
Provider Routes
---------------
GET /api/providers — which LLM providers are configured, and whether each is usable.

The API key stays server-side: availability is reported as a BOOLEAN and the key
itself never enters the response.
"""

from flask import Blueprint, jsonify

from adrag.config import Config
from adrag.custom_packages.rag_pipeline.models.llm import check_ollama

provider_bp = Blueprint("provider", __name__)

_OPENAI_MODELS = [
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-turbo",
    "gpt-3.5-turbo",
]


# ── Routes ────────────────────────────────────────────────────────────────────

@provider_bp.route("/api/providers", methods=["GET"])
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
                "models": _OPENAI_MODELS,
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
