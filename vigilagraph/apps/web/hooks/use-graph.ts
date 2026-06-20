import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type {
  GraphRun,
  GraphNode,
  GraphEdge,
  PaginatedResponse,
  GraphQueryRequest,
  GraphQueryResponse,
} from "@/types/api";

// ─── Runs ────────────────────────────────────────────────
export function useGraphRuns(projectId: string) {
  return useQuery<GraphRun[]>({
    queryKey: ["graph-runs", projectId],
    queryFn: () => api.get<GraphRun[]>(`/graph/${projectId}/runs`),
    enabled: !!projectId,
  });
}

// ─── Latest Run ──────────────────────────────────────────
export function useLatestRun(projectId: string) {
  return useQuery<GraphRun>({
    queryKey: ["graph-latest", projectId],
    queryFn: () => api.get<GraphRun>(`/graph/${projectId}/latest`),
    enabled: !!projectId,
    refetchInterval(query) {
      const data = query.state.data;
      if (!data) return 3000;
      // Poll while running or queued
      if (data.status === "running" || data.status === "queued") return 3000;
      return false;
    },
  });
}

// ─── Generate ────────────────────────────────────────────
export function useGenerateGraph() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (projectId: string) =>
      api.post<GraphRun>(`/graph/${projectId}/generate`),
    onSuccess: (_, projectId) => {
      qc.invalidateQueries({ queryKey: ["graph-runs", projectId] });
      qc.invalidateQueries({ queryKey: ["graph-latest", projectId] });
    },
  });
}

// ─── Nodes ───────────────────────────────────────────────
export function useGraphNodes(
  projectId: string,
  runId: string,
  page = 1,
  filters?: { node_type?: string; community?: number },
) {
  const params = new URLSearchParams({ run_id: runId, page: String(page), page_size: "500" });
  if (filters?.node_type) params.set("node_type", filters.node_type);
  if (filters?.community !== undefined) params.set("community", String(filters.community));

  return useQuery<PaginatedResponse<GraphNode>>({
    queryKey: ["graph-nodes", projectId, runId, page, filters],
    queryFn: () =>
      api.get<PaginatedResponse<GraphNode>>(
        `/graph/${projectId}/nodes?${params.toString()}`,
      ),
    enabled: !!projectId && !!runId,
  });
}

// ─── Edges ───────────────────────────────────────────────
export function useGraphEdges(
  projectId: string,
  runId: string,
  page = 1,
) {
  return useQuery<PaginatedResponse<GraphEdge>>({
    queryKey: ["graph-edges", projectId, runId, page],
    queryFn: () =>
      api.get<PaginatedResponse<GraphEdge>>(
        `/graph/${projectId}/edges?run_id=${runId}&page=${page}&page_size=500`,
      ),
    enabled: !!projectId && !!runId,
  });
}

// ─── Query ───────────────────────────────────────────────
export function useGraphQuery(projectId: string, runId: string) {
  return useMutation({
    mutationFn: (req: GraphQueryRequest) =>
      api.post<GraphQueryResponse>(
        `/graph/${projectId}/query?run_id=${runId}`,
        req,
      ),
  });
}

// ─── Download JSON ───────────────────────────────────────
export function useDownloadGraphJson(projectId: string, runId: string) {
  return useQuery({
    queryKey: ["graph-download-json", projectId, runId],
    queryFn: async () => {
      const data = await api.get<Blob>(
        `/graph/${projectId}/download-json?run_id=${runId}`,
      );
      return data;
    },
    enabled: !!projectId && !!runId,
  });
}

// ─── HTML ────────────────────────────────────────────────
export function useGraphHtml(projectId: string, runId: string) {
  return useQuery<string>({
    queryKey: ["graph-html", projectId, runId],
    queryFn: async () => {
      const res = await api.get<string>(
        `/graph/${projectId}/html?run_id=${runId}`,
      );
      return res;
    },
    enabled: !!projectId && !!runId,
  });
}
