"use client";

import { useParams, usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import { useProject } from "@/hooks/use-projects";
import { useAuth } from "@/hooks/use-auth";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import {
  ArrowLeft,
  LayoutDashboard,
  FileText,
  BookOpen,
  Share2,
  BarChart3,
  FileBarChart,
  Search,
  ScrollText,
} from "lucide-react";
import { cn } from "@/lib/utils";

const statusLabels: Record<string, string> = {
  draft: "Borrador",
  collecting: "Recolectando",
  processing: "Procesando",
  graph_ready: "Grafo listo",
  report_ready: "Informe listo",
  archived: "Archivado",
};

interface Tab {
  label: string;
  href: string;
  icon: React.ElementType;
}

function useProjectTabs(projectId: string): Tab[] {
  return [
    {
      label: "Resumen",
      href: `/projects/${projectId}`,
      icon: LayoutDashboard,
    },
    {
      label: "Búsqueda",
      href: `/projects/${projectId}/search`,
      icon: Search,
    },
    {
      label: "Documentos",
      href: `/projects/${projectId}/documents`,
      icon: FileText,
    },
    {
      label: "Corpus",
      href: `/projects/${projectId}/corpus`,
      icon: BookOpen,
    },
    {
      label: "Grafo",
      href: `/projects/${projectId}/graph`,
      icon: Share2,
    },
    {
      label: "Análisis",
      href: `/projects/${projectId}/analysis`,
      icon: BarChart3,
    },
    {
      label: "Informes",
      href: `/projects/${projectId}/reports`,
      icon: FileBarChart,
    },
    {
      label: "Registros",
      href: `/projects/${projectId}/logs`,
      icon: ScrollText,
    },
  ];
}

export default function ProjectDetailLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const params = useParams();
  const pathname = usePathname();
  const router = useRouter();
  const projectId = params.id as string;
  const { user, loading: authLoading } = useAuth();
  const { data: project, isLoading } = useProject(projectId);
  const tabs = useProjectTabs(projectId);

  // Redirect to login if not authenticated
  if (!authLoading && !user) {
    router.replace("/login");
    return null;
  }

  return (
    <div className="space-y-6">
      {/* Back + Title */}
      <div className="flex items-start gap-4">
        <Button variant="ghost" size="icon" asChild>
          <Link href="/projects">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <div className="flex-1">
          {isLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-6 w-64" />
              <Skeleton className="h-4 w-32" />
            </div>
          ) : project ? (
            <div className="flex items-center gap-3">
              <div>
                <h2 className="text-2xl font-bold tracking-tight">
                  {project.name}
                </h2>
                <p className="text-sm text-muted-foreground">
                  {project.topic}
                </p>
              </div>
              <Badge
                variant={project.status as any}
                className="ml-auto"
              >
                {statusLabels[project.status] || project.status}
              </Badge>
            </div>
          ) : (
            <p className="text-muted-foreground">Proyecto no encontrado</p>
          )}
        </div>
      </div>

      {/* Tab navigation */}
      <nav className="flex gap-1 overflow-x-auto border-b">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive =
            pathname === tab.href ||
            (tab.href !== `/projects/${projectId}` &&
              pathname.startsWith(tab.href));
          return (
            <Link
              key={tab.href}
              href={tab.href}
              className={cn(
                "flex items-center gap-2 whitespace-nowrap border-b-2 px-4 py-3 text-sm font-medium transition-colors",
                isActive
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground",
              )}
            >
              <Icon className="h-4 w-4" />
              {tab.label}
            </Link>
          );
        })}
      </nav>

      {/* Tab content */}
      <div>{children}</div>
    </div>
  );
}
