"use client";

import { useParams } from "next/navigation";
import {
  useCorpusSummary,
  useRebuildCorpus,
  useSeedTestDocs,
} from "@/hooks/use-corpus";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  BookOpen,
  Database,
  RefreshCw,
  Beaker,
  CheckCircle2,
  Clock,
} from "lucide-react";
import { toast } from "sonner";
import { format } from "date-fns";
import { es } from "date-fns/locale";

export default function CorpusPage() {
  const params = useParams();
  const projectId = params.id as string;

  const { data: summary, isLoading } = useCorpusSummary(projectId);
  const rebuildCorpus = useRebuildCorpus();
  const seedTestDocs = useSeedTestDocs();

  const handleRebuild = async () => {
    try {
      await rebuildCorpus.mutateAsync(projectId);
      toast.success("Reconstrucción del corpus iniciada");
    } catch (err: any) {
      toast.error(err?.detail || "Error al reconstruir corpus");
    }
  };

  const handleSeed = async () => {
    try {
      const result = await seedTestDocs.mutateAsync(projectId);
      toast.success(`${result.count} documentos de prueba creados`);
    } catch (err: any) {
      toast.error(err?.detail || "Error al crear docs de prueba");
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }

  const isRebuilding =
    summary?.status === "building" || summary?.status === "processing";
  const progressValue = summary?.total_documents
    ? Math.min(
        100,
        Math.round(((summary.extracted_documents ?? 0) / summary.total_documents) * 100),
      )
    : 0;

  return (
    <div className="space-y-6">
      {/* Summary */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="h-5 w-5" />
            Resumen del corpus
          </CardTitle>
          <CardDescription>
            El corpus es la colección de texto procesado usada para construir el
            grafo de conocimiento.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {summary ? (
            <div className="grid gap-4 sm:grid-cols-3">
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">
                  Total de documentos
                </p>
                <p className="text-2xl font-bold">
                  {summary.total_documents}
                </p>
              </div>
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">Estado</p>
                <Badge
                  variant={
                    summary.status === "ready"
                      ? "graph_ready"
                      : summary.status === "building"
                        ? "processing"
                        : "outline"
                  }
                >
                  {summary.status}
                </Badge>
              </div>
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">
                  Archivos procesados
                </p>
                <p className="text-2xl font-bold">{summary.file_count}</p>
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              No hay datos del corpus disponibles.
            </p>
          )}
        </CardContent>
      </Card>

      {/* Build progress */}
      {isRebuilding && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              <RefreshCw className="h-4 w-4 animate-spin" />
              Construyendo corpus
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Progress value={progressValue} className="h-2" />
            <p className="mt-2 text-xs text-muted-foreground">
              Procesando documentos...
            </p>
          </CardContent>
        </Card>
      )}

      {/* Ready indicator */}
      {summary?.status === "ready" && (
        <Card>
          <CardContent className="flex items-center gap-3 py-4">
            <CheckCircle2 className="h-5 w-5 text-green-500" />
            <div>
              <p className="text-sm font-medium">El corpus está listo</p>
              {summary.last_rebuilt && (
                <p className="text-xs text-muted-foreground">
                  Última reconstrucción{" "}
                  {format(new Date(summary.last_rebuilt), "PPp", {
                    locale: es,
                  })}
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Actions */}
      <div className="flex flex-wrap gap-3">
        <Button
          onClick={handleRebuild}
          disabled={
            rebuildCorpus.isPending || isRebuilding
          }
        >
          <RefreshCw
            className={`mr-2 h-4 w-4 ${rebuildCorpus.isPending ? "animate-spin" : ""}`}
          />
          Reconstruir corpus
        </Button>

        <Button
          variant="outline"
          onClick={handleSeed}
          disabled={seedTestDocs.isPending}
        >
          <Beaker className="mr-2 h-4 w-4" />
          Crear documentos de prueba
        </Button>
      </div>
    </div>
  );
}
