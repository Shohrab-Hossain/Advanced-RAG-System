"""
LangGraph Workflow Builder
---------------------------
Assembles all RAG nodes into a directed graph with:
  - Conditional routing from planner (retrieve / external / direct)
  - Reflection loop: if not grounded and retry budget remains → back to retrieval
  - Linear pipeline for the happy path

Pipeline flow:
  planner
    ├─[retrieve=True]─→ retrieval ─→ external_tools ─→ aggregate
    ├─[use_external only]──────────→ external_tools ─→ aggregate
    └─[direct answer]─────────────────────────────→ aggregate
  aggregate → rerank → compress → reason → reflect
    ├─[not grounded + KB insufficient]─→ retrieval (use_external=True → web search added)
    ├─[not grounded + retry budget]────→ retrieval (loop with same strategy)
    └─[grounded or budget exhausted]───→ END
"""

import os
from langgraph.graph import StateGraph, END

from .state import RAGState
from .generation.planner import planner_node
from .retrieval.node import retrieval_node
from .retrieval.web_node import external_tools_node
from .ranking.aggregator import aggregator_node
from .ranking.reranker import reranker_node
from .generation.compressor import compressor_node
from .generation.reasoning import reasoning_node
from .generation.reflection import reflection_node

MAX_RETRIES = int(os.getenv("MAX_REFLECTION_RETRIES", "2"))


# ── Routing functions ─────────────────────────────────────────────────────────

def _route_planner(state: RAGState) -> str:
    """After planner: decide entry point into the pipeline."""
    if state.get("retrieve", True):
        return "retrieval"
    if state.get("use_external", False):
        return "external_tools"
    return "aggregate"    # direct answer: skip all retrieval


def _route_reflection(state: RAGState) -> str:
    """After reflection: loop back or finish."""
    # final_answer being set signals the reflection node chose to finalize
    if state.get("final_answer"):
        return END
    # Retry: go back to retrieval with incremented retry_count
    return "retrieval"


# ── Graph construction ────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    builder = StateGraph(RAGState)

    # Register nodes
    builder.add_node("planner", planner_node)
    builder.add_node("retrieval", retrieval_node)
    builder.add_node("external_tools", external_tools_node)
    builder.add_node("aggregate", aggregator_node)
    builder.add_node("rerank", reranker_node)
    builder.add_node("compress", compressor_node)
    builder.add_node("reason", reasoning_node)
    builder.add_node("reflect", reflection_node)

    # Entry point
    builder.set_entry_point("planner")

    # Conditional: planner → retrieval | external_tools | aggregate
    builder.add_conditional_edges(
        "planner",
        _route_planner,
        {
            "retrieval": "retrieval",
            "external_tools": "external_tools",
            "aggregate": "aggregate",
        },
    )

    # retrieval always runs external_tools next
    # (external_tools skips itself if use_external=False)
    builder.add_edge("retrieval", "external_tools")
    builder.add_edge("external_tools", "aggregate")

    # Linear pipeline
    builder.add_edge("aggregate", "rerank")
    builder.add_edge("rerank", "compress")
    builder.add_edge("compress", "reason")
    builder.add_edge("reason", "reflect")

    # Conditional: reflect → loop or END
    builder.add_conditional_edges(
        "reflect",
        _route_reflection,
        {"retrieval": "retrieval", END: END},
    )

    return builder.compile()


# Singleton — imported by Flask routes
rag_graph = build_graph()
