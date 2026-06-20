"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { useGraphRuns, useLatestRun, useGenerateGraph } from "@/hooks/use-graph";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Share2,
  Play,
  Eye,
  Loader2,
  Clock,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import { toast } from "sonner";
import { format } from "date-fns";
import { es } from "date-fns/locale";

const runStatusLabels: Record<string, string> = {
  queued: "Queued",
  running: "Running",
  completed: "Completed",
  failed: "Failed",
};

const runStatusVariants: Record<string, any> = {
  queued: "outline",
  running: "processing",
  completed: "graph_ready",
  failed: "destructive",
};

export default function GraphPage() {
  const params = useParams();
  const projectId = params.id as string;

  const { data: runs, isLoading: runsLoading } = useGraphRuns(projectId);
  const { data: latestRun, isLoading: latestLoading } = useLatestRun(projectId);
  const generateGraph = useGenerateGraph();

  const handleGenerate = async () => {
    try {
      await generateGraph.mutateAsync(projectId);
      toast.success("Graph generation started");
    } catch (err: any) {
      toast.error(err?.detail || "Failed to generate graph");
    }
  };

  const isLoading = runsLoading || latestLoading;
  const isRunning = latestRun?.status === "running" || latestRun?.status === "queued";
  const hasGraph = latestRun?.status === "completed";

  return (
    <div className="space-y-6">
      {/* Latest run status */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Share2 className="h-5 w-5" />
            Knowledge Graph
          </CardTitle>
          <CardDescription>
            Generate and explore the knowledge graph extracted from your
            document corpus.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <Skeleton className="h-16 w-full" />
          ) : (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {isRunning ? (
                    <Loader2 className="h-5 w-5 animate-spin text-amber-500" />
                  ) : hasGraph ? (
                    <CheckCircle2 className="h-5 w-5 text-green-500" />
                  ) : latestRun?.status === "failed" ? (
                    <XCircle className="h-5 w-5 text-destructive" />
                  ) : (
                    <Clock className="h-5 w-5 text-muted-foreground" />
                  )}
                  <div>
                    <p className="text-sm font-medium">
                      {latestRun
                        ? `Status: ${runStatusLabels[latestRun.status] || latestRun.status}`
                        : "No graph generated yet"}
                    </p>
                    {latestRun?.error_message && (
                      <p className="text-xs text-destructive">
                        {latestRun.error_message}
                      </p>
                    )}
                    {latestRun?.completed_at && (
                      <p className="text-xs text-muted-foreground">
                        Completed{" "}
                        {format(new Date(latestRun.completed_at), "PPp", {
                          locale: es,
                        })}
                      </p>
                    )}
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button
                    onClick={handleGenerate}
                    disabled={generateGraph.isPending || isRunning}
                  >
                    {generateGraph.isPending ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Play className="mr-2 h-4 w-4" />
                    )}
                    {isRunning ? "Generating..." : "Generate Graph"}
                  </Button>
                  {hasGraph && (
                    <Button variant="outline" asChild>
                      <Link
                        href={`/projects/${projectId}/graph/visualize`}
                      >
                        <Eye className="mr-2 h-4 w-4" />
                        Open Visualization
                      </Link>
                    </Button>
                  )}
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Runs history */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Run History</CardTitle>
          <CardDescription>
            Previous graph generation runs.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {runsLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : !runs || runs.length === 0 ? (
            <div className="py-8 text-center text-sm text-muted-foreground">
              No runs yet. Click &quot;Generate Graph&quot; to start.
            </div>
          ) : (
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Status</TableHead>
                    <TableHead>Started</TableHead>
                    <TableHead>Completed</TableHead>
                    <TableHead>Error</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {runs.map((run) => (
                    <TableRow key={run.id}>
                      <TableCell>
                        <Badge
                          variant={
                            runStatusVariants[run.status] || "outline"
                          }
                        >
                          {runStatusLabels[run.status] || run.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {run.started_at
                          ? format(new Date(run.started_at), "PPp", {
                              locale: es,
                            })
                          : "-"}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {run.completed_at
                          ? format(new Date(run.completed_at), "PPp", {
                              locale: es,
                            })
                          : "-"}
                      </TableCell>
                      <TableCell className="max-w-xs truncate text-sm text-destructive">
                        {run.error_message || "-"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
