"""
Entry Point
-----------
Install once (editable, from Backend/):
    pip install -e .
    pip install -e ".[faiss]"    also the alternative vector backend
    pip install -e ".[prod]"     also gunicorn + gevent-websocket

Run with any of:
    adrag-dev                    the console script pip installs
    python -m adrag.main         the same thing, without the script on PATH
    python src/adrag/main.py     direct, from Backend/

Or with gunicorn for production:
    gunicorn -w 1 -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker \
             --bind 0.0.0.0:5000 adrag.app:app

Note: Use 1 worker with threading for SSE (no forking). The SSE session queues
are process memory and every store is a module singleton, so a second worker
would split the event producer from its consumer.
"""

import logging
import warnings

# Suppress noisy but harmless model-loading messages
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
warnings.filterwarnings("ignore", message=".*position_ids.*")
warnings.filterwarnings("ignore", message="unclosed", category=ResourceWarning)
warnings.filterwarnings("ignore", message=".*huggingface_hub.*token.*")
warnings.filterwarnings("ignore", message=".*unauthenticated.*")
warnings.filterwarnings("ignore", message=".*renamed to.*ddgs.*", category=RuntimeWarning)

from adrag.app import app
from adrag.config import Config


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    """Start the development server. Also the target of the `adrag-dev` script."""
    print(f"Starting RAG API on http://0.0.0.0:{Config.PORT}")
    print(f"LLM model : {Config.LLM_MODEL}")
    print(f"Embedding : {Config.EMBEDDING_MODEL}")
    print(f"Reranker  : {Config.RERANKER_MODEL}")
    app.run(
        debug=Config.DEBUG,
        host="0.0.0.0",
        port=Config.PORT,
        threaded=True,
    )


if __name__ == "__main__":
    main()
