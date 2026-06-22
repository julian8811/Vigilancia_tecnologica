"use client";

import { useParams } from "next/navigation";
import { useProject } from "@/hooks/use-projects";
import { useCollectionRuns } from "@/hooks/use-collection";
import { useGraphRuns } from "@/hooks/use-graph";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
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
import { format } from "date-fns";
import { es } from "date-fns/locale";
import {
  Activity,
  CheckCircle2,
  Clock,
  Database,
  GitGraph,
  Loader2,
  XCircle,
} from "lucide-react";

type RunEvent = {
  id: string;
  type: "collection" | "graph";
  source?: string;
  status: string;
  startedAt?: string | null;
  finishedAt?: string | null;
  message?: string;
  stats?: string;
};

const statusVariant = (status: string) => {
  if (status === "completed") return "graph_ready" as const;
  if (status === "failed") return "destructive" as const;
  if (status === "running") return "processing" as const;
  return "outline" as const;
};

export default function LogsPage() {
  const params = useParams();
  const projectId = params.id as string;
  const { data: project } = useProject(projectId);
  const { data: collectionData, isLoading: collLoading } = useCollectionRuns(projectId, 1, 50);
  const { data: graphData, isLoading: graphLoading } = useGraphRuns(projectId);

  const isLoading = collLoading || graphLoading;

  const events: RunEvent[] = [
    ...(collectionData?.items || []).map((r) => ({
      id: r.id,
      type: "collection" as const,
      source: r.source_name,
      status: r.status,
      startedAt: r.started_at,
      finishedAt: r.finished_at,
      message: r.error_message || undefined,
      stats: r.docs_inserted ? `${r.docs_inserted} / ${r.docs_found} docs` : undefined,
    })),
    ...(Array.isArray(graphData) ? graphData : []).map((r) => ({
      id: r.id,
      type: "graph" as const,
      status: r.status,
      startedAt: r.started_at,
      finishedAt: r.finished_at,
      message: r.error_message || undefined,
      stats: r.node_count ? `${r.node_count} nodes · ${r.edge_count} edges` : undefined,
    })),
  ].sort(
    (a, b) =>
      new Date(b.startedAt || b.finishedAt || 0).getTime() -
      new Date(a.startedAt || a.finishedAt || 0).getTime(),
  );

  const formatDate = (d: string | null | undefined) => {
    if (!d) return "-";
    try {
      return format(new Date(d), "PPp", { locale: es });
    } catch {
      return d;
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Registros de ejecución</h2>
        <p className="text-muted-foreground">
          {project?.name} — historial de ejecución
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            Línea de tiempo
          </CardTitle>
          <CardDescription>
            Ejecuciones de recolección y generación de grafos ordenadas por fecha.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : events.length === 0 ? (
            <div className="py-12 text-center text-muted-foreground">
              <Activity className="mx-auto mb-2 h-8 w-8" />
              <p>No hay ejecuciones todavía. Iniciá la recolección para ver eventos.</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Tipo</TableHead>
                  <TableHead>Estadísticas</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead>Iniciado</TableHead>
                  <TableHead>Error</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {events.map((e) => {
                  const Icon = e.type === "collection" ? Database : GitGraph;

                  return (
                    <TableRow key={`${e.type}-${e.id}`}>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Icon className="h-4 w-4 text-muted-foreground" />
                          <span className="text-sm font-medium capitalize">
                            {e.type}
                          </span>
                          {e.source && (
                            <Badge variant="outline" className="text-[10px]">
                              {e.source}
                            </Badge>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="text-sm">
                        {e.stats || "-"}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1.5">
                          {e.status === "completed" ? (
                            <CheckCircle2 className="h-4 w-4 text-green-600" />
                          ) : e.status === "failed" ? (
                            <XCircle className="h-4 w-4 text-destructive" />
                          ) : e.status === "running" ? (
                            <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
                          ) : (
                            <Clock className="h-4 w-4 text-muted-foreground" />
                          )}
                          <Badge variant={statusVariant(e.status)} className="text-[10px]">
                            {e.status}
                          </Badge>
                        </div>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {formatDate(e.startedAt)}
                      </TableCell>
                      <TableCell className="max-w-[200px] truncate text-xs text-destructive">
                        {e.message || "-"}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
