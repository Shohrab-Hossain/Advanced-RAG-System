"""
Knowledge Base Routes
---------------------
POST   /api/upload                       upload, chunk and index a document
GET    /api/documents                    stats on indexed content
DELETE /api/clear                        wipe every indexed document
GET    /api/knowledge-bases              list uploaded knowledge bases
DELETE /api/knowledge-bases/<file_hash>  remove one knowledge base

The three-store work lives in services.py; these functions are HTTP framing only.
"""

import os
import uuid

from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename

from adrag.config import Config
from adrag.custom_packages.rag_pipeline.ingestion import registry as kb_registry
from adrag.routes.knowledge_base import services

knowledge_base_bp = Blueprint("knowledge_base", __name__)


# ── Helper ────────────────────────────────────────────────────────────────────

def _allowed(filename: str) -> bool:
    """
    First of two extension checks. This one gives a clean 400; _get_loader()'s
    ValueError is the backstop that decides which loader actually runs. Content is
    never sniffed — the extension is trusted to describe the bytes.
    """
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in Config.ALLOWED_EXTENSIONS
    )


# ── Routes ────────────────────────────────────────────────────────────────────

@knowledge_base_bp.route("/api/upload", methods=["POST"])
def upload():
    """Upload a document, chunk it, and index it into all three stores."""
    if "file" not in request.files:
        return jsonify({"error": "No file field in request"}), 400

    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "Empty filename"}), 400
    if not _allowed(f.filename):
        return jsonify({
            "error": f"Unsupported file type. Allowed: {', '.join(sorted(Config.ALLOWED_EXTENSIONS))}"
        }), 400

    # secure_filename runs BEFORE the join — it is the sole path-traversal defence here.
    filename = secure_filename(f.filename)
    file_path = os.path.join(Config.UPLOAD_FOLDER, filename)
    f.save(file_path)

    try:
        payload, _ = services.index_document(file_path, filename, str(uuid.uuid4()))
        return jsonify(payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 422
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@knowledge_base_bp.route("/api/documents", methods=["GET"])
def documents():
    """Return current index statistics."""
    return jsonify(services.index_stats())


@knowledge_base_bp.route("/api/clear", methods=["DELETE"])
def clear():
    """Wipe all indexed documents from all stores and delete uploaded files."""
    services.clear_everything()
    return jsonify({"success": True, "message": "All documents cleared"})


@knowledge_base_bp.route("/api/knowledge-bases", methods=["GET"])
def list_knowledge_bases():
    """Return all uploaded knowledge bases with per-KB stats."""
    return jsonify({"knowledge_bases": kb_registry.list_all()})


@knowledge_base_bp.route("/api/knowledge-bases/<file_hash>", methods=["DELETE"])
def delete_knowledge_base(file_hash):
    """Remove a specific knowledge base from all stores and delete its uploaded file."""
    kb_entry = kb_registry.get(file_hash)
    services.remove_document(file_hash)
    if kb_entry:
        services.delete_upload(kb_entry["name"])
    return jsonify({"success": True, "stats": services.totals()})
