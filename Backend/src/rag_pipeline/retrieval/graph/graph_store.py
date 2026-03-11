"""
Graph Store
------------
NetworkX-based knowledge graph for entity-aware (GraphRAG) retrieval.
Entities extracted from document chunks are linked in a bipartite graph;
queries traverse up to 2 hops to surface related document nodes.
"""

import os
import pickle
import re
from collections import defaultdict
from typing import Dict, List, Set

import networkx as nx

from config import Config

GRAPH_PATH = os.getenv("GRAPH_PATH", Config.GRAPH_PATH)

# Words to ignore when extracting entities
_STOP_WORDS = {
    "The", "This", "That", "With", "From", "For", "And", "But", "Are",
    "Was", "Has", "Have", "Its", "Our", "Their", "Will", "Can", "May",
    "Also", "Such", "When", "Where", "How", "What", "Which",
}


class GraphStore:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        os.makedirs(os.path.dirname(GRAPH_PATH), exist_ok=True)
        self.graph = nx.Graph()
        self.doc_store: Dict[str, dict] = {}
        self._load()
        self._initialized = True

    # ── Entity extraction ─────────────────────────────────────────────────────

    def _extract_entities(self, text: str) -> Set[str]:
        entities: Set[str] = set()
        # Multi-word proper nouns (e.g. "Google Cloud", "New York")
        for m in re.findall(r"\b[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})*\b", text):
            if m not in _STOP_WORDS and len(m) > 2:
                entities.add(m)
        # Acronyms (e.g. "LLM", "RAG", "API")
        for m in re.findall(r"\b[A-Z]{2,6}\b", text):
            entities.add(m)
        # camelCase technical terms
        for m in re.findall(r"\b[a-z]+(?:[A-Z][a-z]+)+\b", text):
            entities.add(m)
        return entities

    # ── Public API ────────────────────────────────────────────────────────────

    def add_document(self, doc_id: str, content: str, metadata: dict) -> None:
        """Index a document chunk and connect it to its entities."""
        entities = self._extract_entities(content)
        self.graph.add_node(
            doc_id, type="document",
            content_preview=content[:200], metadata=metadata,
        )
        self.doc_store[doc_id] = {"content": content, "metadata": metadata}

        for entity in entities:
            eid = f"entity:{entity.lower()}"
            if not self.graph.has_node(eid):
                self.graph.add_node(eid, type="entity", name=entity, count=0)
            self.graph.nodes[eid]["count"] = self.graph.nodes[eid].get("count", 0) + 1

            if self.graph.has_edge(doc_id, eid):
                self.graph[doc_id][eid]["weight"] += 1
            else:
                self.graph.add_edge(doc_id, eid, weight=1)

        self._save()

    def search(self, query: str, top_k: int = 5) -> List[dict]:
        """Find documents related to entities in the query (2-hop traversal)."""
        query_entities = self._extract_entities(query)
        if not query_entities:
            return []

        doc_scores: Dict[str, float] = defaultdict(float)

        for entity in query_entities:
            eid = f"entity:{entity.lower()}"
            if not self.graph.has_node(eid):
                continue
            # 1st hop: documents directly connected to this entity
            for nbr in self.graph.neighbors(eid):
                if self.graph.nodes[nbr].get("type") == "document":
                    doc_scores[nbr] += self.graph[eid][nbr].get("weight", 1) * 2.0
            # 2nd hop: documents sharing related entities
            for nbr in list(self.graph.neighbors(eid)):
                if self.graph.nodes[nbr].get("type") == "entity":
                    for doc_nbr in self.graph.neighbors(nbr):
                        if self.graph.nodes[doc_nbr].get("type") == "document":
                            doc_scores[doc_nbr] += 0.5

        top = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        results = []
        for doc_id, score in top:
            data = self.doc_store.get(doc_id, {})
            results.append({
                "content": data.get("content", ""),
                "metadata": data.get("metadata", {}),
                "score": float(score),
                "source": "graph",
                "rerank_score": 0.0,
            })
        return results

    def delete_by_file(self, file_hash: str) -> None:
        """Remove all document nodes for a file and orphaned entity nodes."""
        to_remove = [
            nid for nid, d in self.graph.nodes(data=True)
            if d.get("type") == "document"
            and self.doc_store.get(nid, {}).get("metadata", {}).get("file_hash") == file_hash
        ]
        for nid in to_remove:
            self.graph.remove_node(nid)
            self.doc_store.pop(nid, None)
        orphans = [
            nid for nid, d in self.graph.nodes(data=True)
            if d.get("type") == "entity" and self.graph.degree(nid) == 0
        ]
        self.graph.remove_nodes_from(orphans)
        self._save()

    def count_entities_by_file(self, file_hash: str) -> int:
        chunk_ids = {
            nid for nid in self.doc_store
            if self.doc_store[nid].get("metadata", {}).get("file_hash") == file_hash
        }
        entity_set = set()
        for cid in chunk_ids:
            if self.graph.has_node(cid):
                for nbr in self.graph.neighbors(cid):
                    if self.graph.nodes[nbr].get("type") == "entity":
                        entity_set.add(nbr)
        return len(entity_set)

    def get_stats(self) -> dict:
        doc_nodes = sum(1 for _, d in self.graph.nodes(data=True) if d.get("type") == "document")
        ent_nodes = sum(1 for _, d in self.graph.nodes(data=True) if d.get("type") == "entity")
        return {
            "documents": doc_nodes,
            "entities": ent_nodes,
            "edges": self.graph.number_of_edges(),
        }

    def clear(self) -> None:
        self.graph.clear()
        self.doc_store.clear()
        self._save()

    # ── Persistence ───────────────────────────────────────────────────────────

    def _save(self) -> None:
        with open(GRAPH_PATH, "wb") as f:
            pickle.dump({"graph": self.graph, "doc_store": self.doc_store}, f)

    def _load(self) -> None:
        if os.path.exists(GRAPH_PATH):
            try:
                with open(GRAPH_PATH, "rb") as f:
                    data = pickle.load(f)
                    self.graph = data["graph"]
                    self.doc_store = data["doc_store"]
            except Exception:
                self.graph = nx.Graph()
                self.doc_store = {}


graph_store = GraphStore()
