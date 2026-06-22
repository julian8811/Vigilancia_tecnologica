import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type {
  Project,
  ProjectListResponse,
  ProjectCreate,
  SearchStrategy,
} from "@/types/api";

// ─── List ────────────────────────────────────────────────
export function useProjects(page = 1, pageSize = 20) {
  return useQuery<ProjectListResponse>({
    queryKey: ["projects", page, pageSize],
    queryFn: () =>
      api.get<ProjectListResponse>(
        `/projects?page=${page}&page_size=${pageSize}`,
      ),
  });
}

// ─── Detail ──────────────────────────────────────────────
export function useProject(id: string) {
  return useQuery<Project>({
    queryKey: ["project", id],
    queryFn: () => api.get<Project>(`/projects/${id}`),
    enabled: !!id,
  });
}

// ─── Create ──────────────────────────────────────────────
export function useCreateProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ProjectCreate) =>
      api.post<Project>("/projects", data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["projects"] });
    },
  });
}

// ─── Update ──────────────────────────────────────────────
export function useUpdateProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<ProjectCreate> }) =>
      api.put<Project>(`/projects/${id}`, data),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ["projects"] });
      qc.invalidateQueries({ queryKey: ["project", vars.id] });
    },
  });
}

// ─── Delete ──────────────────────────────────────────────
export function useDeleteProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete(`/projects/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["projects"] });
    },
  });
}

// ─── Duplicate ───────────────────────────────────────────
export function useDuplicateProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api.post<Project>(`/projects/${id}/duplicate`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["projects"] });
    },
  });
}

// ─── Archive ─────────────────────────────────────────────
export function useArchiveProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api.post<Project>(`/projects/${id}/archive`),
    onSuccess: (_, id) => {
      qc.invalidateQueries({ queryKey: ["projects"] });
      qc.invalidateQueries({ queryKey: ["project", id] });
    },
  });
}

// ─── Transition Status ───────────────────────────────────
export function useTransitionStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      status,
    }: {
      id: string;
      status: string;
    }) =>
      api.post<Project>(`/projects/${id}/status`, { status }),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ["projects"] });
      qc.invalidateQueries({ queryKey: ["project", vars.id] });
    },
  });
}

// ─── Search Strategy ─────────────────────────────────────
export function useSearchStrategy(projectId: string) {
  return useQuery<SearchStrategy>({
    queryKey: ["search-strategy", projectId],
    queryFn: () =>
      api.get<SearchStrategy>(`/projects/${projectId}/search-strategy`),
    enabled: !!projectId,
  });
}

export function useUpdateSearchStrategy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      projectId,
      data,
    }: {
      projectId: string;
      data: Partial<SearchStrategy>;
    }) => api.put<SearchStrategy>(`/projects/${projectId}/search-strategy`, data),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({
        queryKey: ["search-strategy", vars.projectId],
      });
    },
  });
}

export function useGenerateSearchStrategy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (projectId: string) =>
      api.post<SearchStrategy>(
        `/projects/${projectId}/search-strategy/generate`,
      ),
    onSuccess: (_, projectId) => {
      qc.invalidateQueries({
        queryKey: ["search-strategy", projectId],
      });
    },
  });
}
