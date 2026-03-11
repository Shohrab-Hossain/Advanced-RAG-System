"""
Knowledge Base Registry
------------------------
Tracks uploaded files as named knowledge bases with indexing stats.
Persisted to JSON so it survives server restarts.
"""

import json
import os
import threading
from datetime import datetime, timezone

from config import Config

_REGISTRY_PATH = os.getenv("KB_REGISTRY_PATH", os.path.join(Config.DATABASE_ROOT, "kb_registry.json"))

# migrate legacy registry location
if os.path.exists("./data/kb_registry.json") and not os.path.exists(_REGISTRY_PATH):
    os.makedirs(os.path.dirname(_REGISTRY_PATH), exist_ok=True)
    import shutil
    shutil.move("./data/kb_registry.json", _REGISTRY_PATH)
_lock = threading.Lock()


def _load() -> dict:
    if os.path.exists(_REGISTRY_PATH):
        try:
            with open(_REGISTRY_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save(data: dict) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(_REGISTRY_PATH)), exist_ok=True)
    with open(_REGISTRY_PATH, "w") as f:
        json.dump(data, f, indent=2)


def register(file_hash: str, file_name: str, stats: dict) -> dict:
    """Add or update a KB entry. Returns the stored entry."""
    with _lock:
        data = _load()
        entry = {
            "id": file_hash,
            "name": file_name,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "chunks": stats.get("chunks", 0),
            "vectors": stats.get("vectors", 0),
            "entities": stats.get("entities", 0),
            "edges": stats.get("edges", 0),
        }
        data[file_hash] = entry
        _save(data)
        return entry


def list_all() -> list:
    """Return all KBs sorted newest first."""
    with _lock:
        return sorted(
            _load().values(),
            key=lambda x: x.get("uploaded_at", ""),
            reverse=True,
        )


def remove(file_hash: str) -> bool:
    with _lock:
        data = _load()
        if file_hash in data:
            del data[file_hash]
            _save(data)
            return True
        return False


def clear_all() -> None:
    with _lock:
        _save({})
