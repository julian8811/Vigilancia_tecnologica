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

export function useGraphRuns(projectId: string) {
  return useQuery<GraphRun[]>({
    queryKey: ["graph-runs", projectId],
    queryFn: async () => {
      const data = await api.get<PaginatedResponse<GraphRun>>(
        `/projects/${projectId}/graph/runs`,
      );
      return data.items ?? [];
    },
    enabled: !!projectId,
  });
}

export function useLatestRun(projectId: string) {
  return useQuery<GraphRun>({
    queryKey: ["graph-latest", projectId],
    queryFn: () => api.get<GraphRun>(`/projects/${projectId}/graph/latest`),
    enabled: !!projectId,
    refetchInterval(query) {
      const data = query.state.data;
      if (!data) return 3000;
      if (data.status === "running" || data.status === "queued") return 3000;
      return false;
    },
  });
}

export function useGenerateGraph() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (projectId: string) =>
      api.post<GraphRun>(`/projects/${projectId}/graph/generate`),
    onSuccess: (_, projectId) => {
      qc.invalidateQueries({ queryKey: ["graph-runs", projectId] });
      qc.invalidateQueries({ queryKey: ["graph-latest", projectId] });
    },
  });
}

export function useGraphNodes(
  projectId: string,
  runId: string,
  page = 1,
  filters?: { node_type?: string; community?: number },
) {
  const params = new URLSearchParams({ page: String(page), page_size: "200" });
  if (filters?.node_type) params.set("node_type", filters.node_type);
  if (filters?.community !== undefined) params.set("community", String(filters.community));

  return useQuery<PaginatedResponse<GraphNode>>({
    queryKey: ["graph-nodes", projectId, runId, page, filters],
    queryFn: () =>
      api.get<PaginatedResponse<GraphNode>>(
        `/projects/${projectId}/graph/runs/${runId}/nodes?${params.toString()}`,
      ),
    enabled: !!projectId && !!runId,
  });
}

export function useGraphEdges(
  projectId: string,
  runId: string,
  page = 1,
) {
  return useQuery<PaginatedResponse<GraphEdge>>({
    queryKey: ["graph-edges", projectId, runId, page],
    queryFn: () =>
      api.get<PaginatedResponse<GraphEdge>>(
        `/projects/${projectId}/graph/runs/${runId}/edges?page=${page}&page_size=200`,
      ),
    enabled: !!projectId && !!runId,
  });
}

export function useGraphQuery(projectId: string) {
  return useMutation({
    mutationFn: (req: GraphQueryRequest) =>
      api.post<GraphQueryResponse>(
        `/projects/${projectId}/graph/query`,
        req,
      ),
  });
}

export function useDownloadGraphJson(projectId: string, runId: string) {
  return useQuery<Blob | null>({
    queryKey: ["graph-download-json", projectId, runId],
    queryFn: async () => {
      const res = await api.getRaw(
        `/projects/${projectId}/graph/download-json?run_id=${runId}`,
      );
      return res.blob();
    },
    enabled: !!projectId && !!runId,
  });
}

export function useGraphHtml(projectId: string, runId: string) {
  return useQuery<string | null>({
    queryKey: ["graph-html", projectId, runId],
    queryFn: async () => {
      const res = await api.getRaw(
        `/projects/${projectId}/graph/html?run_id=${runId}`,
      );
      return res.text();
    },
    enabled: !!projectId && !!runId,
  });
}
