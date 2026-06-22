"use client";

import { useParams } from "next/navigation";
import { useState } from "react";
import { useProject } from "@/hooks/use-projects";
import {
  useTechnologies,
  useTrends,
  useActors,
  useOpportunities,
  useRunAnalysis,
} from "@/hooks/use-analysis";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
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
  Loader2,
  BarChart3,
  Brain,
  TrendingUp,
  Users,
  Lightbulb,
  Play,
} from "lucide-react";
import { toast } from "sonner";

export default function AnalysisPage() {
  const params = useParams();
  const projectId = params.id as string;
  const { data: project } = useProject(projectId);
  const { data: technologies, isLoading: techLoading } = useTechnologies(projectId);
  const { data: trends, isLoading: trendsLoading } = useTrends(projectId);
  const { data: actors, isLoading: actorsLoading } = useActors(projectId);
  const { data: opportunities, isLoading: oppsLoading } = useOpportunities(projectId);
  const runAnalysis = useRunAnalysis();
  const [topic, setTopic] = useState("");

  const handleRunAnalysis = async () => {
    if (!topic && !project?.topic) {
      toast.error("Ingresá un tema o usá el tema del proyecto");
      return;
    }
    try {
      await runAnalysis.mutateAsync({
        projectId,
        topic: topic || project?.topic || "",
      });
      toast.success("Análisis iniciado");
    } catch (err: any) {
      toast.error(err?.detail || "Error en el análisis");
    }
  };

  const isLoading = techLoading || trendsLoading || actorsLoading || oppsLoading;

  const trendBadge = (momentum: string | null | undefined) => {
    const variants: Record<string, string> = {
      emerging: "bg-blue-100 text-blue-800",
      growing: "bg-green-100 text-green-800",
      stable: "bg-gray-100 text-gray-800",
      declining: "bg-red-100 text-red-800",
      uncertain: "bg-yellow-100 text-yellow-800",
    };
    return variants[momentum || ""] || "bg-gray-100 text-gray-800";
  };

  return (
    <div className="space-y-6">
      {/* Run Analysis */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Brain className="h-5 w-5" />
            Análisis con IA
          </CardTitle>
          <CardDescription>
            Ejecutá el análisis con IA para identificar tecnologías, tendencias, actores y oportunidades.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex gap-3">
            <Input
              placeholder="Tema de análisis (por defecto el tema del proyecto)"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
            />
            <Button
              onClick={handleRunAnalysis}
              disabled={runAnalysis.isPending}
            >
              {runAnalysis.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Play className="mr-2 h-4 w-4" />
              )}
              Ejecutar análisis
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Stats */}
      {!isLoading && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Tecnologías</CardTitle>
              <BarChart3 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">{technologies?.total || 0}</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Tendencias</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">{trends?.total || 0}</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Actores</CardTitle>
              <Users className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">{actors?.total || 0}</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Oportunidades</CardTitle>
              <Lightbulb className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">{opportunities?.total || 0}</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Technologies */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5" />
            Tecnologías
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <Skeleton className="h-32 w-full" />
          ) : !technologies?.items?.length ? (
            <p className="text-sm text-muted-foreground">Ejecutá el análisis para identificar tecnologías.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nombre</TableHead>
                  <TableHead>Categoría</TableHead>
                  <TableHead>TRL</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {technologies.items.map((t) => (
                  <TableRow key={t.id}>
                    <TableCell>{t.name}</TableCell>
                    <TableCell>{t.category || "-"}</TableCell>
                    <TableCell>{t.trl_level || "-"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Trends */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            Tendencias
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <Skeleton className="h-32 w-full" />
          ) : !trends?.items?.length ? (
            <p className="text-sm text-muted-foreground">Ejecutá el análisis para detectar tendencias.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Tendencia</TableHead>
                  <TableHead>Dirección</TableHead>
                  <TableHead>Descripción</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {trends.items.map((t) => (
                  <TableRow key={t.id}>
                    <TableCell className="font-medium">{t.name}</TableCell>
                    <TableCell>
                      <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${trendBadge(t.momentum)}`}>
                        {t.momentum || "N/D"}
                      </span>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {t.description || "-"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Actors */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="h-5 w-5" />
            Actores clave
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <Skeleton className="h-32 w-full" />
          ) : !actors?.items?.length ? (
            <p className="text-sm text-muted-foreground">Ejecutá el análisis para identificar actores.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nombre</TableHead>
                  <TableHead>Tipo</TableHead>
                  <TableHead>País</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {actors.items.map((a) => (
                  <TableRow key={a.id}>
                    <TableCell className="font-medium">{a.name}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{a.actor_type || "N/D"}</Badge>
                    </TableCell>
                    <TableCell>{a.country || "-"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Opportunities */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Lightbulb className="h-5 w-5" />
            Oportunidades
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <Skeleton className="h-32 w-full" />
          ) : !opportunities?.items?.length ? (
            <p className="text-sm text-muted-foreground">Ejecutá el análisis para detectar oportunidades.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Title</TableHead>
                  <TableHead>Tipo</TableHead>
                  <TableHead>Prioridad</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {opportunities.items.map((o) => (
                  <TableRow key={o.id}>
                    <TableCell className="font-medium">{o.title}</TableCell>
                    <TableCell>
                      <Badge variant="secondary">{o.opportunity_type || "N/D"}</Badge>
                    </TableCell>
                    <TableCell>{o.priority || "-"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
