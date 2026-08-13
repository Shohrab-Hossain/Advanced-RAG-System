"""
Entry Point
-----------
Run with:
    cd Backend
    python src/main.py

Or with gunicorn for production:
    cd Backend
    gunicorn -w 1 -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker \
             --bind 0.0.0.0:5000 --chdir src main:app

Note: Use 1 worker with threading for SSE (no forking).
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
