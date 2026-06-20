import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { CorpusSummary } from "@/types/api";

// ─── Summary ─────────────────────────────────────────────
export function useCorpusSummary(projectId: string) {
  return useQuery<CorpusSummary>({
    queryKey: ["corpus", projectId, "summary"],
    queryFn: () =>
      api.get<CorpusSummary>(`/corpus/${projectId}/summary`),
    enabled: !!projectId,
  });
}

// ─── Rebuild ─────────────────────────────────────────────
export function useRebuildCorpus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (projectId: string) =>
      api.post<{ status: string }>(`/corpus/${projectId}/rebuild`),
    onSuccess: (_, projectId) => {
      qc.invalidateQueries({ queryKey: ["corpus", projectId] });
    },
  });
}

// ─── Seed Test Docs ──────────────────────────────────────
export function useSeedTestDocs() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (projectId: string) =>
      api.post<{ status: string; count: number }>(
        `/corpus/${projectId}/seed-test-docs`,
      ),
    onSuccess: (_, projectId) => {
      qc.invalidateQueries({ queryKey: ["documents", projectId] });
      qc.invalidateQueries({ queryKey: ["corpus", projectId] });
    },
  });
}
