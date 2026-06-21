import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import type { GraphNode, GraphEdge, PaginatedResponse } from "@/types/api";

interface UseGraphDataResult {
  nodes: GraphNode[];
  edges: GraphEdge[];
  loading: boolean;
  error: Error | null;
}

export function useGraphData(
  projectId: string,
  runId?: string,
): UseGraphDataResult {
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (!projectId || !runId) return;

    let cancelled = false;

    const fetchAll = async () => {
      setLoading(true);
      setError(null);
      setNodes([]);
      setEdges([]);

      try {
        const allNodes: GraphNode[] = [];
        let page = 1;

        while (true) {
          const nodeData = await api.get<PaginatedResponse<GraphNode>>(
            `/projects/${projectId}/graph/runs/${runId}/nodes?page=${page}&page_size=500`,
          );
          allNodes.push(...nodeData.items);
          if (page >= nodeData.total_pages) break;
          page++;
        }

        page = 1;
        const allEdges: GraphEdge[] = [];
        while (true) {
          const edgeData = await api.get<PaginatedResponse<GraphEdge>>(
            `/projects/${projectId}/graph/runs/${runId}/edges?page=${page}&page_size=500`,
          );
          allEdges.push(...edgeData.items);
          if (page >= edgeData.total_pages) break;
          page++;
        }

        if (!cancelled) {
          setNodes(allNodes);
          setEdges(allEdges);
        }
      } catch (e) {
        if (!cancelled) setError(e as Error);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetchAll();

    return () => {
      cancelled = true;
    };
  }, [projectId, runId]);

  return { nodes, edges, loading, error };
}
