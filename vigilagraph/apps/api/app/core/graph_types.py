"""Shared type maps for Graphify knowledge-graph node and edge types."""

NODE_TYPE_MAP: dict[str, str] = {
    "technology": "technology",
    "paper": "paper",
    "author": "author",
    "institution": "institution",
    "concept": "concept",
    "topic": "topic",
    "method": "method",
    "application": "application",
    "material": "material",
    "organization": "organization",
    "person": "person",
    "location": "location",
    "event": "event",
    "product": "product",
    "dataset": "dataset",
    "tool": "tool",
    "field": "field",
    "subfield": "subfield",
}

EDGE_TYPE_MAP: dict[str, str] = {
    "related_to": "related_to",
    "cites": "cites",
    "authored_by": "authored_by",
    "developed_by": "developed_by",
    "uses_method": "uses_method",
    "mentions": "mentions",
    "part_of": "part_of",
    "application_of": "application_of",
    "improves": "improves",
    "precedes": "precedes",
    "collaborates_with": "collaborates_with",
    "funded_by": "funded_by",
}
