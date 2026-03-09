# advanced_rag_pipeline.py
# Full Self-RAG + ColBERT + GraphRAG + LangGraph Pipeline

from langgraph.graph import StateGraph
from langchain_openai import ChatOpenAI
from typing import List, TypedDict
import random

# -----------------------------
# 1️⃣ Define RAG State
# -----------------------------
class RAGState(TypedDict):
    query: str
    retrieve: bool
    docs: List[str]
    context: List[str]
    answer: str

# -----------------------------
# 2️⃣ Initialize LLM
# -----------------------------
llm = ChatOpenAI(model="gpt-4o-mini")

# -----------------------------
# 3️⃣ Planner / Self-RAG Decision
# -----------------------------
def planner_node(state: RAGState):
    query = state["query"]
    decision = llm.invoke(f"Do we need to retrieve documents for this query? {query}")
    return {"retrieve": "yes" in decision.content.lower()}

# -----------------------------
# 4️⃣ Hybrid Retrieval Node
# -----------------------------
def retrieval_node(state: RAGState):
    if not state.get("retrieve", True):
        return {"docs": []}

    query = state["query"]

    # Simulated retrieval for demonstration
    vector_docs = [f"VectorDB doc about {query}"]
    colbert_docs = [f"ColBERT token-level match for {query}"]
    graph_docs = [f"GraphRAG node info about {query}"]

    all_docs = vector_docs + colbert_docs + graph_docs
    return {"docs": all_docs}

# -----------------------------
# 5️⃣ Evidence Aggregator
# -----------------------------
def aggregate_node(state: RAGState):
    docs = state.get("docs", [])
    # Remove duplicates
    return {"docs": list(set(docs))}

# -----------------------------
# 6️⃣ Reranker Node
# -----------------------------
def rerank_node(state: RAGState):
    docs = state.get("docs", [])
    # Simulated ranking: random shuffle and pick top 5
    random.shuffle(docs)
    return {"context": docs[:5]}

# -----------------------------
# 7️⃣ Context Compression
# -----------------------------
def compress_node(state: RAGState):
    context = state.get("context", [])
    # Truncate each doc to first 200 chars
    compressed = [c[:200] for c in context]
    return {"context": compressed}

# -----------------------------
# 8️⃣ Reasoning / Generation
# -----------------------------
def reasoning_node(state: RAGState):
    context = "\n".join(state.get("context", []))
    query = state["query"]

    prompt = f"""
Answer the question using only the context below.

Context:
{context}

Question:
{query}
"""

    answer = llm.invoke(prompt)
    return {"answer": answer.content}

# -----------------------------
# 9️⃣ Reflection / Self-Check
# -----------------------------
def reflection_node(state: RAGState):
    answer = state.get("answer", "")
    context = "\n".join(state.get("context", []))
    query = state["query"]

    prompt = f"""
Check if the answer is supported by the evidence.

Question:
{query}

Answer:
{answer}

Context:
{context}

Respond YES if supported, NO if unsupported.
"""
    result = llm.invoke(prompt)
    if "no" in result.content.lower():
        return {"answer": "Answer not supported by retrieved documents."}
    return {}

# -----------------------------
# 10️⃣ Build LangGraph Workflow
# -----------------------------
builder = StateGraph(RAGState)

builder.add_node("planner", planner_node)
builder.add_node("retrieval", retrieval_node)
builder.add_node("aggregate", aggregate_node)
builder.add_node("rerank", rerank_node)
builder.add_node("compress", compress_node)
builder.add_node("reason", reasoning_node)
builder.add_node("reflect", reflection_node)

builder.set_entry_point("planner")

builder.add_edge("planner", "retrieval")
builder.add_edge("retrieval", "aggregate")
builder.add_edge("aggregate", "rerank")
builder.add_edge("rerank", "compress")
builder.add_edge("compress", "reason")
builder.add_edge("reason", "reflect")

graph = builder.compile()

# -----------------------------
# 11️⃣ Run the Pipeline
# -----------------------------
if __name__ == "__main__":
    query = "Which company created Kubernetes and what other tools do they maintain?"
    result = graph.invoke({"query": query})
    print("✅ Final Answer:\n", result["answer"])