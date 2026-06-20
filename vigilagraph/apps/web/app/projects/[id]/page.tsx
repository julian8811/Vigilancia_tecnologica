"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { useProject } from "@/hooks/use-projects";
import { useDocuments } from "@/hooks/use-documents";
import { useLatestRun } from "@/hooks/use-graph";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import {
  FileText,
  Share2,
  Globe,
  Languages,
  FileType,
  Calendar,
} from "lucide-react";
import { format } from "date-fns";
import { es } from "date-fns/locale";

const statusLabels: Record<string, string> = {
  draft: "Draft",
  collecting: "Collecting",
  processing: "Processing",
  graph_ready: "Graph Ready",
  report_ready: "Report Ready",
  archived: "Archived",
};

const typeLabels: Record<string, string> = {
  patent: "Patent",
  scientific: "Scientific",
  news: "News",
  social: "Social",
  full: "Full (all sources)",
};

export default function ProjectOverviewPage() {
  const params = useParams();
  const projectId = params.id as string;
  const { data: project, isLoading } = useProject(projectId);
  const { data: docsData } = useDocuments(projectId, 1, 1);
  const { data: latestRun } = useLatestRun(projectId);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <div className="grid gap-4 sm:grid-cols-2">
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
        </div>
      </div>
    );
  }

  if (!project) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          Project not found.
        </CardContent>
      </Card>
    );
  }

  const docCount = docsData?.total ?? 0;

  return (
    <div className="space-y-6">
      {/* Description */}
      {project.description && (
        <Card>
          <CardHeader>
            <CardTitle>Description</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              {project.description}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Info cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Surveillance Type
            </CardTitle>
            <Globe className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <p className="text-lg font-semibold capitalize">
              {typeLabels[project.surveillance_type] ||
                project.surveillance_type}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Language</CardTitle>
            <Languages className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <p className="text-lg font-semibold uppercase">
              {project.language}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Status</CardTitle>
            <FileType className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <Badge variant={project.status as any}>
              {statusLabels[project.status] || project.status}
            </Badge>
          </CardContent>
        </Card>
      </div>

      {/* Quick actions */}
      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-4 w-4" />
              Documents
            </CardTitle>
            <CardDescription>
              {docCount > 0
                ? `${docCount} document${docCount !== 1 ? "s" : ""} uploaded`
                : "No documents yet"}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button variant="outline" size="sm" asChild>
              <Link href={`/projects/${projectId}/documents`}>
                <FileText className="mr-2 h-4 w-4" />
                Manage Documents
              </Link>
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Share2 className="h-4 w-4" />
              Knowledge Graph
            </CardTitle>
            <CardDescription>
              {latestRun
                ? `Status: ${latestRun.status}`
                : "No graph generated yet"}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button variant="outline" size="sm" asChild>
              <Link href={`/projects/${projectId}/graph`}>
                <Share2 className="mr-2 h-4 w-4" />
                View Graph
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Creation info */}
      <p className="text-xs text-muted-foreground">
        Created{" "}
        {format(new Date(project.created_at), "PPp", { locale: es })} — Last
        updated{" "}
        {format(new Date(project.updated_at), "PPp", { locale: es })}
      </p>
    </div>
  );
}
