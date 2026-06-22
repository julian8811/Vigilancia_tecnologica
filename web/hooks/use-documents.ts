import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type {
  Document,
  DocumentListResponse,
} from "@/types/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function useDocuments(
  projectId: string,
  page = 1,
  pageSize = 20,
) {
  return useQuery<DocumentListResponse>({
    queryKey: ["documents", projectId, page, pageSize],
    queryFn: () =>
      api.get<DocumentListResponse>(
        `/projects/${projectId}/documents?page=${page}&page_size=${pageSize}`,
      ),
    enabled: !!projectId,
  });
}

export function useUploadDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      projectId,
      file,
    }: {
      projectId: string;
      file: File;
    }) => {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("project_id", projectId);
      const token = localStorage.getItem("token");
      const res = await fetch(`${API_URL}/api/v1/projects/${projectId}/documents/upload`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ error: "Upload failed" }));
        throw new Error(err.error || "Upload failed");
      }
      return res.json() as Promise<Document>;
    },
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ["documents", vars.projectId] });
    },
  });
}

export function useAddUrlDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { project_id: string; url: string; title?: string }) =>
      api.post<Document>(`/projects/${data.project_id}/documents/add-url`, { url: data.url, title: data.title }),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ["documents", vars.project_id] });
    },
  });
}

export function useDeleteDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ projectId, docId }: { projectId: string; docId: string }) =>
      api.delete(`/projects/${projectId}/documents/${docId}`),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ["documents", vars.projectId] });
    },
  });
}

export function useReprocessDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ projectId, docId }: { projectId: string; docId: string }) =>
      api.post<Document>(`/projects/${projectId}/documents/${docId}/reprocess`),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ["documents", vars.projectId] });
    },
  });
}
