// Hooks for analysis data — technologies, trends, actors, opportunities, and reports.

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type {
  TechnologyListResponse,
  TrendListResponse,
  ActorListResponse,
  OpportunityListResponse,
  ReportListResponse,
  Report,
} from "@/types/api";

// ─── Technologies ──────────────────────────────────────────

export function useTechnologies(
  projectId: string,
  params?: { page?: number; pageSize?: number; category?: string },
) {
  const { page = 1, pageSize = 50, category } = params || {};
  const searchParams = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  if (category) searchParams.set("category", category);

  return useQuery<TechnologyListResponse>({
    queryKey: ["technologies", projectId, params],
    queryFn: () =>
      api.get<TechnologyListResponse>(
        `/projects/${projectId}/technologies?${searchParams}`,
      ),
    enabled: !!projectId,
  });
}

// ─── Trends ────────────────────────────────────────────────

export function useTrends(
  projectId: string,
  params?: { page?: number; trendType?: string },
) {
  const { page = 1, trendType } = params || {};
  const searchParams = new URLSearchParams({ page: String(page) });
  if (trendType) searchParams.set("trend_type", trendType);

  return useQuery<TrendListResponse>({
    queryKey: ["trends", projectId, params],
    queryFn: () =>
      api.get<TrendListResponse>(
        `/projects/${projectId}/trends?${searchParams}`,
      ),
    enabled: !!projectId,
  });
}

// ─── Actors ────────────────────────────────────────────────

export function useActors(
  projectId: string,
  params?: { page?: number; actorType?: string },
) {
  const { page = 1, actorType } = params || {};
  const searchParams = new URLSearchParams({ page: String(page) });
  if (actorType) searchParams.set("actor_type", actorType);

  return useQuery<ActorListResponse>({
    queryKey: ["actors", projectId, params],
    queryFn: () =>
      api.get<ActorListResponse>(
        `/projects/${projectId}/actors?${searchParams}`,
      ),
    enabled: !!projectId,
  });
}

// ─── Opportunities ────────────────────────────────────────

export function useOpportunities(
  projectId: string,
  params?: { page?: number; opportunityType?: string },
) {
  const { page = 1, opportunityType } = params || {};
  const searchParams = new URLSearchParams({ page: String(page) });
  if (opportunityType) searchParams.set("opportunity_type", opportunityType);

  return useQuery<OpportunityListResponse>({
    queryKey: ["opportunities", projectId, params],
    queryFn: () =>
      api.get<OpportunityListResponse>(
        `/projects/${projectId}/opportunities?${searchParams}`,
      ),
    enabled: !!projectId,
  });
}

// ─── Run Analysis ─────────────────────────────────────────

export function useRunAnalysis() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      projectId,
      topic,
    }: {
      projectId: string;
      topic: string;
    }) =>
      api.post(`/projects/${projectId}/analysis/run`, {
        topic,
      }),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ["technologies", vars.projectId] });
      qc.invalidateQueries({ queryKey: ["trends", vars.projectId] });
      qc.invalidateQueries({ queryKey: ["actors", vars.projectId] });
      qc.invalidateQueries({ queryKey: ["opportunities", vars.projectId] });
      qc.invalidateQueries({ queryKey: ["project", vars.projectId] });
    },
  });
}

// ─── Reports ──────────────────────────────────────────────

export function useReports(
  projectId: string,
  params?: { page?: number; pageSize?: number },
) {
  const { page = 1, pageSize = 50 } = params || {};
  return useQuery<ReportListResponse>({
    queryKey: ["reports", projectId, params],
    queryFn: () =>
      api.get<ReportListResponse>(
        `/projects/${projectId}/reports?page=${page}&page_size=${pageSize}`,
      ),
    enabled: !!projectId,
  });
}

export function useGenerateReport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      projectId,
      title,
      reportType,
    }: {
      projectId: string;
      title: string;
      reportType?: string;
    }) =>
      api.post<Report>(`/projects/${projectId}/reports`, {
        title,
        report_type: reportType || "complete",
      }),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ["reports", vars.projectId] });
    },
  });
}
