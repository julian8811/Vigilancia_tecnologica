"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { useProject, useSearchStrategy } from "@/hooks/use-projects";
import { useDocuments } from "@/hooks/use-documents";
import { useLatestRun } from "@/hooks/use-graph";
import { useTriggerCollection } from "@/hooks/use-collection";
import { useCorpusSummary } from "@/hooks/use-corpus";
import { useTechnologies, useTrends, useActors, useOpportunities } from "@/hooks/use-analysis";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import {
  Search,
  FileText,
  BookOpen,
  Share2,
  BarChart3,
  FileBarChart,
  CheckCircle2,
  ArrowRight,
  Loader2,
  Circle,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface PipelineStep {
  key: string;
  label: string;
  icon: React.ElementType;
  href: string;
  ready: boolean;
  summary: string;
}

export default function ProjectOverviewPage() {
  const params = useParams();
  const projectId = params.id as string;
  const { data: project, isLoading } = useProject(projectId);
  const { data: docsData } = useDocuments(projectId, 1, 1);
  const { data: latestRun } = useLatestRun(projectId);
  const { data: strategy } = useSearchStrategy(projectId);
  const { data: corpus } = useCorpusSummary(projectId);
  const { data: techData } = useTechnologies(projectId);
  const { data: trendsData } = useTrends(projectId);
  const { data: actorsData } = useActors(projectId);
  const { data: oppData } = useOpportunities(projectId);
  const triggerCollection = useTriggerCollection();

  if (isLoading || !project) {
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

  const docCount = docsData?.total ?? 0;
  const hasStrategy = !!(strategy?.keywords_en || strategy?.keywords_es || strategy?.boolean_queries);
  const hasCorpus = !!(corpus?.corpus_ready);
  const hasGraph = !!(latestRun && latestRun.status === "completed");
  const hasAnalysis = !!(techData && techData.total > 0);
  const hasReports = false; // reports check via separate query if needed

  const steps: PipelineStep[] = [
    {
      key: "search",
      label: "Define Search",
      icon: Search,
      href: `/projects/${projectId}/search`,
      ready: hasStrategy,
      summary: hasStrategy
        ? `Keywords configured${strategy?.boolean_queries ? " with AI-generated boolean queries" : ""}`
        : "Choose keywords and sources for document collection",
    },
    {
      key: "documents",
      label: "Collect Documents",
      icon: FileText,
      href: `/projects/${projectId}/documents`,
      ready: docCount > 0,
      summary: docCount > 0
        ? `${docCount} document${docCount !== 1 ? "s" : ""} collected`
        : "Search academic databases and upload documents",
    },
    {
      key: "corpus",
      label: "Build Corpus",
      icon: BookOpen,
      href: `/projects/${projectId}/corpus`,
      ready: hasCorpus,
      summary: hasCorpus
        ? `Corpus ready — ${corpus?.total_documents ?? 0} documents extracted`
        : "Extract text and prepare documents for analysis",
    },
    {
      key: "graph",
      label: "Generate Graph",
      icon: Share2,
      href: `/projects/${projectId}/graph`,
      ready: hasGraph,
      summary: hasGraph
        ? `Knowledge graph ready — ${latestRun?.node_count ?? 0} nodes, ${latestRun?.edge_count ?? 0} edges`
        : "Run Graphify to build a knowledge graph from the corpus",
    },
    {
      key: "analysis",
      label: "AI Analysis",
      icon: BarChart3,
      href: `/projects/${projectId}/analysis`,
      ready: hasAnalysis,
      summary: hasAnalysis
        ? [
            techData && techData.total > 0 ? `${techData.total} technologies` : null,
            trendsData && trendsData.total > 0 ? `${trendsData.total} trends` : null,
            actorsData && actorsData.total > 0 ? `${actorsData.total} actors` : null,
            oppData && oppData.total > 0 ? `${oppData.total} opportunities` : null,
          ].filter(Boolean).join(" · ")
        : "AI-powered identification of technologies, trends, actors and opportunities",
    },
    {
      key: "reports",
      label: "Generate Report",
      icon: FileBarChart,
      href: `/projects/${projectId}/reports`,
      ready: hasAnalysis,
      summary: hasAnalysis
        ? "Ready to generate HTML, PDF, and Markdown reports"
        : "Create comprehensive surveillance reports from the analysis",
    },
  ];

  const firstIncomplete = steps.findIndex((s) => !s.ready);

  return (
    <div className="space-y-6">
      {/* Description */}
      {project.description && (
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">{project.description}</p>
          </CardContent>
        </Card>
      )}

      {/* Pipeline */}
      <Card>
        <CardHeader>
          <CardTitle>Pipeline Progress</CardTitle>
          <CardDescription>
            Complete each step in order to generate your surveillance report.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-1">
          {steps.map((step, i) => {
            const isCurrent = i === firstIncomplete;
            const isPast = i < firstIncomplete;

            return (
              <div
                key={step.key}
                className={cn(
                  "flex items-start gap-4 rounded-lg border p-4 transition-colors",
                  isCurrent && "border-primary bg-primary/5",
                  isPast && "border-green-200 bg-green-50/30",
                  !isPast && !isCurrent && "border-transparent bg-muted/30",
                )}
              >
                <div className="flex flex-col items-center pt-1">
                  {isPast ? (
                    <CheckCircle2 className="h-5 w-5 text-green-600" />
                  ) : isCurrent ? (
                    <div className="flex h-5 w-5 items-center justify-center rounded-full bg-primary text-[10px] font-bold text-primary-foreground">
                      {i + 1}
                    </div>
                  ) : (
                    <Circle className="h-5 w-5 text-muted-foreground/40" />
                  )}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <step.icon className={cn(
                      "h-4 w-4",
                      isPast ? "text-green-600" : isCurrent ? "text-primary" : "text-muted-foreground",
                    )} />
                    <span className={cn(
                      "font-medium text-sm",
                      isPast ? "text-green-700" : isCurrent ? "text-primary" : "text-muted-foreground",
                    )}>
                      {step.label}
                    </span>
                    {isPast && (
                      <Badge variant="graph_ready" className="text-[10px] px-1.5 py-0">Done</Badge>
                    )}
                    {isCurrent && (
                      <Badge variant="processing" className="text-[10px] px-1.5 py-0">Next</Badge>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground mb-2">
                    {step.summary}
                  </p>
                  <Button variant={isCurrent ? "default" : "outline"} size="sm" asChild>
                    <Link href={step.href}>
                      {step.ready ? "View" : "Start"}
                      <ArrowRight className="ml-1 h-3 w-3" />
                    </Link>
                  </Button>
                </div>

                {step.key === "documents" && hasStrategy && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => triggerCollection.mutate(projectId)}
                    disabled={triggerCollection.isPending}
                    className="shrink-0"
                  >
                    {triggerCollection.isPending ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      "Collect Now"
                    )}
                  </Button>
                )}
              </div>
            );
          })}
        </CardContent>
      </Card>

      {/* Metadata */}
      <p className="text-xs text-muted-foreground">
        Created {project.created_at ? new Date(project.created_at).toLocaleDateString() : "—"}
        {" · "}
        Status: <Badge variant={project.status as any} className="text-[10px] px-1.5 py-0">{project.status}</Badge>
        {" · "}
        Type: {project.surveillance_type || "—"}
        {" · "}
        Language: {project.language || "—"}
      </p>
    </div>
  );
}
