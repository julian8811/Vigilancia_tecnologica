"""Tests for GraphJsonParser — pure graph JSON parsing logic."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.core.graph_types import EDGE_TYPE_MAP, NODE_TYPE_MAP
from worker.graphify.parser import (
    GraphJsonParser,
    ParsedEdge,
    ParsedGraph,
    ParsedNode,
)


@pytest.fixture
def parser() -> GraphJsonParser:
    return GraphJsonParser()


@pytest.fixture
def sample_data() -> dict:
    """A minimal but realistic graph.json payload."""
    return {
        "nodes": [
            {"id": "n1", "label": "CRISPR", "type": "technology", "community": 0, "centrality": 0.85},
            {"id": "n2", "label": "Gene Editing in Crops", "type": "application", "community": 0, "centrality": 0.72},
            {"id": "n3", "label": "Zhang, F.", "type": "person", "community": 1},
        ],
        "edges": [
            {"source": "n2", "target": "n1", "type": "application_of", "weight": 0.9},
            {"source": "n3", "target": "n1", "type": "developed_by", "weight": 0.8},
        ],
        "community_count": 2,
        "title": "CRISPR Graph",
        "generated_at": "2026-06-20T10:00:00Z",
    }


# ── ParsedNode ────────────────────────────────────────────


class TestParsedNode:
    def test_minimal_node(self):
        node = ParsedNode(external_id="x1", label="Test")
        assert node.external_id == "x1"
        assert node.label == "Test"
        assert node.node_type is None
        assert node.community_id is None
        assert node.centrality_score is None
        assert node.metadata == {}


# ── ParsedEdge ────────────────────────────────────────────


class TestParsedEdge:
    def test_minimal_edge(self):
        edge = ParsedEdge(source_external_id="s1", target_external_id="t1")
        assert edge.source_external_id == "s1"
        assert edge.target_external_id == "t1"
        assert edge.edge_type is None
        assert edge.weight is None


# ── ParsedGraph ───────────────────────────────────────────


class TestParsedGraph:
    def test_empty_graph(self):
        g = ParsedGraph()
        assert g.nodes == []
        assert g.edges == []
        assert g.community_count == 0
        assert g.stats == {}
        assert g.metadata == {}


# ── GraphJsonParser ───────────────────────────────────────


class TestGraphJsonParser:
    def test_parse_empty(self, parser: GraphJsonParser):
        result = parser.parse_dict({})
        assert isinstance(result, ParsedGraph)
        assert result.nodes == []
        assert result.edges == []
        assert result.stats["total_nodes"] == 0

    def test_parse_sample(self, parser: GraphJsonParser, sample_data: dict):
        result = parser.parse_dict(sample_data)
        assert len(result.nodes) == 3
        assert len(result.edges) == 2
        assert result.community_count == 2

    def test_parse_node_fields(self, parser: GraphJsonParser):
        data = {
            "nodes": [
                {"id": "n1", "label": "CRISPR", "type": "technology", "community": 0, "centrality": 0.85},
            ],
            "edges": [],
        }
        result = parser.parse_dict(data)
        node = result.nodes[0]
        assert node.external_id == "n1"
        assert node.label == "CRISPR"
        assert node.node_type == "technology"
        assert node.community_id == 0
        assert node.centrality_score == 0.85

    def test_parse_node_fallback_fields(self, parser: GraphJsonParser):
        """Should fall back to 'name' when 'label' is missing."""
        data = {"nodes": [{"id": "n1", "name": "Fallback"}], "edges": []}
        result = parser.parse_dict(data)
        assert result.nodes[0].label == "Fallback"

    def test_parse_node_type_mapping(self, parser: GraphJsonParser):
        """Node types should use NODE_TYPE_MAP."""
        for raw_type, expected in NODE_TYPE_MAP.items():
            data = {"nodes": [{"id": "n1", "label": "Test", "type": raw_type}], "edges": []}
            result = parser.parse_dict(data)
            assert result.nodes[0].node_type == expected, f"Raw type '{raw_type}' → '{expected}'"

    def test_parse_edge_fields(self, parser: GraphJsonParser):
        data = {
            "nodes": [],
            "edges": [
                {"source": "s1", "target": "t1", "type": "cites", "weight": 0.75},
            ],
        }
        result = parser.parse_dict(data)
        edge = result.edges[0]
        assert edge.source_external_id == "s1"
        assert edge.target_external_id == "t1"
        assert edge.edge_type == "cites"
        assert edge.weight == 0.75

    def test_parse_edge_type_mapping(self, parser: GraphJsonParser):
        for raw_type, expected in EDGE_TYPE_MAP.items():
            data = {"nodes": [], "edges": [{"source": "s", "target": "t", "type": raw_type}]}
            result = parser.parse_dict(data)
            assert result.edges[0].edge_type == expected, f"Raw edge type '{raw_type}' → '{expected}'"

    def test_parse_metadata(self, parser: GraphJsonParser, sample_data: dict):
        result = parser.parse_dict(sample_data)
        assert result.metadata["title"] == "CRISPR Graph"
        assert "generated_at" in result.metadata

    def test_parse_stats(self, parser: GraphJsonParser, sample_data: dict):
        result = parser.parse_dict(sample_data)
        assert result.stats["total_nodes"] == 3
        assert result.stats["total_edges"] == 2
        assert result.stats["community_count"] == 2
        assert result.stats["has_centrality"] is True
        assert result.stats["has_communities"] is True

    def test_parse_stats_no_communities(self, parser: GraphJsonParser):
        """When no community data exists, stats should reflect that."""
        data = {
            "nodes": [{"id": "n1", "label": "Lonely"}],
            "edges": [],
        }
        result = parser.parse_dict(data)
        assert result.stats["has_communities"] is False
        assert result.stats["community_count"] == 0

    def test_parse_node_label_truncated(self, parser: GraphJsonParser):
        """Labels longer than 500 chars should be truncated."""
        long_label = "A" * 1000
        data = {"nodes": [{"id": "n1", "label": long_label}], "edges": []}
        result = parser.parse_dict(data)
        assert len(result.nodes[0].label) == 500

    def test_parse_edge_alternative_weight_key(self, parser: GraphJsonParser):
        """Should accept 'strength' as an alternative to 'weight'."""
        data = {
            "nodes": [],
            "edges": [{"source": "s", "target": "t", "type": "cites", "strength": 0.5}],
        }
        result = parser.parse_dict(data)
        assert result.edges[0].weight == 0.5

    def test_parse_file(self, parser: GraphJsonParser, tmp_path: Path, sample_data: dict):
        """parse_file should read from disk and delegate to parse_dict."""
        filepath = tmp_path / "graph.json"
        filepath.write_text(json.dumps(sample_data), encoding="utf-8")
        result = parser.parse_file(filepath)
        assert len(result.nodes) == 3
        assert result.metadata["title"] == "CRISPR Graph"
