"""
RAG Pipeline
------------
The eight-node LangGraph pipeline, wired in workflow.py:

  planner → retrieval → external_tools → aggregate → rerank → compress → reason → reflect

`planner` and `reflect` are conditional edges — the planner is a Self-RAG decision
node, and `reflect` can loop back for up to MAX_REFLECTION_RETRIES further attempts.

An SSE `stage` id is NOT the graph node name — 5 of the 8 differ. The emit() call
sites are the contract the frontend's tracker matches on, never workflow.py's
add_node() names.
"""
