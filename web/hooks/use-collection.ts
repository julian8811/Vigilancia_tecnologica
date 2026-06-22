import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type {
  CollectionRun,
  CollectionRunListResponse,
  Project,
} from "@/types/api";

// ─── List Collection Runs ─────────────────────────────────
export function useCollectionRuns(projectId: string, page = 1, pageSize = 20) {
  return useQuery<CollectionRunListResponse>({
    queryKey: ["collection-runs", projectId, page, pageSize],
    queryFn: () =>
      api.get<CollectionRunListResponse>(
        `/projects/${projectId}/collection-runs?page=${page}&page_size=${pageSize}`,
      ),
    enabled: !!projectId,
  });
}

// ─── Trigger Collection ───────────────────────────────────
export function useTriggerCollection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (projectId: string) =>
      api.post<Project>(`/projects/${projectId}/status`, { status: "collecting" }),
    onSuccess: (_, projectId) => {
      qc.invalidateQueries({ queryKey: ["project", projectId] });
      qc.invalidateQueries({ queryKey: ["collection-runs", projectId] });
      qc.invalidateQueries({ queryKey: ["projects"] });
    },
  });
}

// ─── Latest Collection Runs (last 3) ──────────────────────
export function useLatestCollectionRuns(projectId: string) {
  return useQuery<CollectionRun[]>({
    queryKey: ["collection-runs-latest", projectId],
    queryFn: async () => {
      const data = await api.get<CollectionRunListResponse>(
        `/projects/${projectId}/collection-runs?page=1&page_size=3`,
      );
      return data.items;
    },
    enabled: !!projectId,
    refetchInterval(query) {
      const items = query.state.data;
      if (!items) return 3000;
      const hasActive = items.some(
        (r) => r.status === "pending" || r.status === "running",
      );
      return hasActive ? 3000 : false;
    },
  });
}
