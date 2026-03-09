"""
Entry Point
-----------
Run with:
    cd Backend
    python main.py

Or with gunicorn for production:
    gunicorn -w 1 -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker \
             --bind 0.0.0.0:5000 main:app

Note: Use 1 worker with threading for SSE (no forking).
"""

import logging
import warnings

# Suppress noisy but harmless model-loading messages
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
warnings.filterwarnings("ignore", message=".*position_ids.*")

from app import app, Config

if __name__ == "__main__":
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
