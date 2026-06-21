import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { CorpusSummary } from "@/types/api";

export function useCorpusSummary(projectId: string) {
  return useQuery<CorpusSummary>({
    queryKey: ["corpus", projectId, "summary"],
    queryFn: () =>
      api.get<CorpusSummary>(`/projects/${projectId}/corpus/summary`),
    enabled: !!projectId,
  });
}

export function useRebuildCorpus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (projectId: string) =>
      api.post<{ status: string }>(`/projects/${projectId}/corpus/rebuild`),
    onSuccess: (_, projectId) => {
      qc.invalidateQueries({ queryKey: ["corpus", projectId] });
    },
  });
}

export function useSeedTestDocs() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (projectId: string) =>
      api.post<{ status: string; count: number }>(
        `/projects/${projectId}/corpus/seed-test-docs`,
      ),
    onSuccess: (_, projectId) => {
      qc.invalidateQueries({ queryKey: ["documents", projectId] });
      qc.invalidateQueries({ queryKey: ["corpus", projectId] });
    },
  });
}
