"use client";

import { useParams, usePathname } from "next/navigation";
import Link from "next/link";
import { useProject } from "@/hooks/use-projects";
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
  draft: "Draft",
  collecting: "Collecting",
  processing: "Processing",
  graph_ready: "Graph Ready",
  report_ready: "Report Ready",
  archived: "Archived",
};

interface Tab {
  label: string;
  href: string;
  icon: React.ElementType;
}

function useProjectTabs(projectId: string): Tab[] {
  return [
    {
      label: "Overview",
      href: `/projects/${projectId}`,
      icon: LayoutDashboard,
    },
    {
      label: "Search",
      href: `/projects/${projectId}/search`,
      icon: Search,
    },
    {
      label: "Documents",
      href: `/projects/${projectId}/documents`,
      icon: FileText,
    },
    {
      label: "Corpus",
      href: `/projects/${projectId}/corpus`,
      icon: BookOpen,
    },
    {
      label: "Graph",
      href: `/projects/${projectId}/graph`,
      icon: Share2,
    },
    {
      label: "Analysis",
      href: `/projects/${projectId}/analysis`,
      icon: BarChart3,
    },
    {
      label: "Reports",
      href: `/projects/${projectId}/reports`,
      icon: FileBarChart,
    },
    {
      label: "Logs",
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
  const projectId = params.id as string;
  const { data: project, isLoading } = useProject(projectId);
  const tabs = useProjectTabs(projectId);

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
            <p className="text-muted-foreground">Project not found</p>
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
