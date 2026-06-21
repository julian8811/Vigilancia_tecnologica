"""GraphJsonParser — parse graphify output JSON into structured domain objects."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.core.graph_types import NODE_TYPE_MAP, EDGE_TYPE_MAP


@dataclass
class ParsedNode:
    """A single node from the knowledge graph."""
    external_id: str
    label: str
    node_type: str | None = None
    community_id: int | None = None
    centrality_score: float | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class ParsedEdge:
    """A single edge (relationship) from the knowledge graph."""
    source_external_id: str
    target_external_id: str
    edge_type: str | None = None
    weight: float | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class ParsedGraph:
    """Complete parsed knowledge graph ready for DB import."""
    nodes: list[ParsedNode] = field(default_factory=list)
    edges: list[ParsedEdge] = field(default_factory=list)
    community_count: int = 0
    stats: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)


class GraphJsonParser:
    """Parse the ``graph.json`` file produced by Graphify CLI."""

    def parse_file(self, path: str | Path) -> ParsedGraph:
        """Read and parse a graph.json file from disk."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return self.parse_dict(data)

    def parse_dict(self, data: dict[str, Any]) -> ParsedGraph:
        """Parse a parsed JSON dictionary into structured domain objects."""
        # Parse nodes
        raw_nodes = data.get("nodes", [])
        nodes = [self._parse_node(n) for n in raw_nodes]

        # Parse edges
        raw_edges = data.get("edges", [])
        edges = [self._parse_edge(e) for e in raw_edges]

        # Extract community count
        community_count = data.get("community_count", 0)

        # Collect stats
        stats = {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "community_count": community_count,
            "has_centrality": any(n.centrality_score is not None for n in nodes),
            "has_communities": any(n.community_id is not None for n in nodes),
        }

        # Collect metadata
        meta = {}
        for key in ("title", "description", "version", "generated_at", "parameters"):
            if key in data:
                meta[key] = data[key]

        return ParsedGraph(
            nodes=nodes,
            edges=edges,
            community_count=community_count,
            stats=stats,
            metadata=meta,
        )

    def _parse_node(self, data: dict[str, Any]) -> ParsedNode:
        """Parse a single node dict."""
        node_id = str(data.get("id", ""))
        label = str(data.get("label", data.get("name", "unknown")))
        raw_type = data.get("type", "concept")
        node_type = NODE_TYPE_MAP.get(str(raw_type).lower(), str(raw_type))

        community = data.get("community", data.get("community_id"))
        centrality = data.get("centrality", data.get("centrality_score"))

        metadata = {}
        for key in ("description", "url", "source", "aliases", "mentions", "properties"):
            if key in data:
                metadata[key] = data[key]

        return ParsedNode(
            external_id=node_id,
            label=str(label)[:500],
            node_type=str(node_type)[:50],
            community_id=int(community) if community is not None else None,
            centrality_score=float(centrality) if centrality is not None else None,
            metadata=metadata,
        )

    def _parse_edge(self, data: dict[str, Any]) -> ParsedEdge:
        """Parse a single edge dict."""
        source = str(data.get("source", ""))
        target = str(data.get("target", ""))
        raw_type = data.get("type", "related_to")
        edge_type = EDGE_TYPE_MAP.get(str(raw_type).lower(), str(raw_type))
        weight = data.get("weight", data.get("strength"))

        metadata = {}
        for key in ("label", "properties", "source", "evidence"):
            if key in data:
                metadata[key] = data[key]

        return ParsedEdge(
            source_external_id=source,
            target_external_id=target,
            edge_type=str(edge_type)[:50],
            weight=float(weight) if weight is not None else None,
            metadata=metadata,
        )
