"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/hooks/use-auth";
import { useProjects } from "@/hooks/use-projects";
import { RequireAuth } from "@/components/auth/require-auth";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import {
  FolderKanban,
  Plus,
  FileText,
  BarChart3,
  CheckCircle2,
  Archive,
} from "lucide-react";
import type { Project } from "@/types/api";

const statusLabels: Record<string, string> = {
  draft: "Borrador",
  collecting: "Recolectando",
  processing: "Procesando",
  graph_ready: "Grafo listo",
  report_ready: "Informe listo",
  archived: "Archivado",
};

export default function DashboardPage() {
  const router = useRouter();
  const { user } = useAuth();
  const { data: projectsData, isLoading } = useProjects(1, 100);

  useEffect(() => {
    if (!isLoading && projectsData && projectsData.total === 0) {
      router.push("/onboarding");
    }
  }, [isLoading, projectsData, router]);

  const projects = projectsData?.items || [];
  const totalProjects = projects.length;
  const graphReady = projects.filter(
    (p) => p.status === "graph_ready" || p.status === "report_ready",
  ).length;
  const collecting = projects.filter((p) => p.status === "collecting" || p.status === "processing").length;
  const archived = projects.filter((p) => p.status === "archived").length;
  const recentProjects = projects.slice(0, 5);

  return (
    <RequireAuth>
    <div className="space-y-6">
      {/* Welcome */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">
            Welcome back{user?.name ? `, ${user.name}` : ""}!
          </h2>
          <p className="text-muted-foreground">
            Este es el resumen de tus proyectos de vigilancia.
          </p>
        </div>
        <Button asChild>
          <Link href="/projects/create">
            <Plus className="mr-2 h-4 w-4" />
            Nuevo proyecto
          </Link>
        </Button>
      </div>

      {/* Stats */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Total de proyectos
            </CardTitle>
            <FolderKanban className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <div className="text-2xl font-bold">{totalProjects}</div>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              En progreso
            </CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <div className="text-2xl font-bold">{collecting}</div>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Grafo listo
            </CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <div className="text-2xl font-bold">{graphReady}</div>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Archivado</CardTitle>
            <Archive className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <div className="text-2xl font-bold">{archived}</div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Recent Projects */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Proyectos recientes</CardTitle>
            <CardDescription>
              Tus proyectos actualizados recientemente.
            </CardDescription>
          </div>
          <Button variant="outline" size="sm" asChild>
            <Link href="/projects">Ver todos</Link>
          </Button>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : recentProjects.length === 0 ? (
            <div className="flex flex-col items-center gap-3 py-8 text-center">
              <FolderKanban className="h-12 w-12 text-muted-foreground/50" />
              <div>
                <p className="font-medium">No hay proyectos todavía</p>
                <p className="text-sm text-muted-foreground">
                  Creá tu primer proyecto de vigilancia para empezar.
                </p>
              </div>
              <Button asChild>
                <Link href="/projects/create">
                  <Plus className="mr-2 h-4 w-4" />
                  Crear proyecto
                </Link>
              </Button>
            </div>
          ) : (
            <div className="space-y-2">
              {recentProjects.map((project) => (
                <Link
                  key={project.id}
                  href={`/projects/${project.id}`}
                  className="flex items-center justify-between rounded-lg border p-3 transition-colors hover:bg-accent"
                >
                  <div className="flex items-center gap-3">
                    <div>
                      <p className="text-sm font-medium">{project.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {project.topic}
                      </p>
                    </div>
                  </div>
                  <Badge variant={project.status as any}>
                    {statusLabels[project.status] || project.status}
                  </Badge>
                </Link>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
    </RequireAuth>
  );
}
