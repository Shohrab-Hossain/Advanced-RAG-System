"""
SSE Event Bus
--------------
Each query gets a unique session_id. Pipeline nodes call emit() to push
events into that session's queue. The Flask SSE route drains the queue
and forwards events to the browser as text/event-stream.
"""

import json
import queue
import uuid
from typing import Optional, Tuple

# session_id → Queue
_sessions: dict[str, queue.Queue] = {}


def create_session(session_id: Optional[str] = None) -> Tuple[str, queue.Queue]:
    """Create a new event queue for a pipeline run."""
    if session_id is None:
        session_id = str(uuid.uuid4())
    q: queue.Queue = queue.Queue()
    _sessions[session_id] = q
    return session_id, q


def get_queue(session_id: str) -> Optional[queue.Queue]:
    return _sessions.get(session_id)


def emit(session_id: Optional[str], event_type: str, data: dict) -> None:
    """Push a typed event into the session queue (no-op if session gone)."""
    if not session_id:
        return
    q = _sessions.get(session_id)
    if q:
        q.put({"type": event_type, "data": data})


def close_session(session_id: str) -> None:
    """Push the end sentinel and remove the queue."""
    q = _sessions.get(session_id)
    if q:
        q.put(None)           # Sentinel → SSE generator exits
    _sessions.pop(session_id, None)


def format_sse(payload: dict) -> str:
    """Serialize a dict as an SSE data frame."""
    return f"data: {json.dumps(payload)}\n\n"
