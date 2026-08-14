"""
adRAG Backend
-------------
The Flask REST + SSE API wrapped around the LangGraph RAG pipeline.

  app.py            the application factory — CORS, blueprint registration
  config.py         environment-driven configuration
  main.py           the development entry point
  routes/           the routed layer — one folder per resource
  custom_packages/  capabilities nothing routes to, consumed by the routes
"""

__version__ = "0.1.0"
