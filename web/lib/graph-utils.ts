import cytoscape from "cytoscape";
import type { GraphNode, GraphEdge } from "@/types/api";

/**
 * Convert API graph nodes and edges to Cytoscape.js elements format.
 */
export function elementsToCyData(
  nodes: GraphNode[],
  edges: GraphEdge[],
): cytoscape.ElementDefinition[] {
  const cyNodes: cytoscape.ElementDefinition[] = nodes.map((n) => ({
    group: "nodes",
    data: {
      id: n.id,
      label: n.label,
      nodeType: n.node_type,
      community: n.community_id ?? 0,
      centrality: n.centrality_score ?? 0,
      metadata: n.metadata_json,
      externalNodeId: n.external_node_id,
    },
  }));

  const cyEdges: cytoscape.ElementDefinition[] = edges.map((e) => ({
    group: "edges",
    data: {
      id: e.id,
      source: e.source_node_id,
      target: e.target_node_id,
      edgeType: e.edge_type,
      weight: e.weight ?? 1,
      metadata: e.metadata_json,
    },
  }));

  return [...cyNodes, ...cyEdges];
}

/**
 * Client-side filter for graph nodes.
 */
export function filterNodes(
  nodes: GraphNode[],
  filters: {
    search?: string;
    types?: string[];
    communities?: number[];
  },
): GraphNode[] {
  return nodes.filter((n) => {
    if (filters.search) {
      const q = filters.search.toLowerCase();
      if (!n.label.toLowerCase().includes(q)) return false;
    }
    if (filters.types && filters.types.length > 0) {
      if (!filters.types.includes(n.node_type)) return false;
    }
    if (filters.communities && filters.communities.length > 0) {
      if (
        n.community_id !== undefined &&
        !filters.communities.includes(n.community_id)
      )
        return false;
    }
    return true;
  });
}

const COMMUNITY_COLORS = [
  "#6366f1", // indigo
  "#ec4899", // pink
  "#14b8a6", // teal
  "#f59e0b", // amber
  "#8b5cf6", // violet
  "#10b981", // emerald
  "#f97316", // orange
  "#3b82f6", // blue
  "#eab308", // yellow
  "#84cc16", // lime
  "#06b6d4", // cyan
  "#a855f7", // purple
  "#ef4444", // red
  "#22c55e", // green
  "#0ea5e9", // sky
];

/**
 * Return a stable color for a given community id.
 */
export function communityColor(communityId: number): string {
  return COMMUNITY_COLORS[communityId % COMMUNITY_COLORS.length];
}

const NODE_TYPE_COLORS: Record<string, string> = {
  concept: "#6366f1",
  technology: "#ec4899",
  organization: "#14b8a6",
  person: "#f59e0b",
  patent: "#8b5cf6",
  paper: "#10b981",
  product: "#f97316",
  default: "#6b7280",
};

/**
 * Return a color for a given node type.
 */
export function getNodeTypeColor(nodeType: string): string {
  return NODE_TYPE_COLORS[nodeType] || NODE_TYPE_COLORS.default;
}

/**
 * Return top N nodes by centrality.
 */
export function topNodes(
  nodes: GraphNode[],
  limit: number = 10,
): GraphNode[] {
  return [...nodes]
    .sort((a, b) => (b.centrality_score ?? 0) - (a.centrality_score ?? 0))
    .slice(0, limit);
}
