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
      toast.error("Enter a topic or use the project's topic");
      return;
    }
    try {
      await runAnalysis.mutateAsync({
        projectId,
        topic: topic || project?.topic || "",
      });
      toast.success("Analysis started");
    } catch (err: any) {
      toast.error(err?.detail || "Analysis failed");
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
            AI Analysis
          </CardTitle>
          <CardDescription>
            Run AI analysis to identify technologies, trends, actors, and opportunities.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex gap-3">
            <Input
              placeholder="Analysis topic (defaults to project topic)"
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
              Run Analysis
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Stats */}
      {!isLoading && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Technologies</CardTitle>
              <BarChart3 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">{technologies?.total || 0}</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Trends</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">{trends?.total || 0}</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Actors</CardTitle>
              <Users className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">{actors?.total || 0}</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Opportunities</CardTitle>
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
            Technologies
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <Skeleton className="h-32 w-full" />
          ) : !technologies?.items?.length ? (
            <p className="text-sm text-muted-foreground">Run analysis to identify technologies.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Category</TableHead>
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
            Trends
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <Skeleton className="h-32 w-full" />
          ) : !trends?.items?.length ? (
            <p className="text-sm text-muted-foreground">Run analysis to detect trends.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Trend</TableHead>
                  <TableHead>Direction</TableHead>
                  <TableHead>Description</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {trends.items.map((t) => (
                  <TableRow key={t.id}>
                    <TableCell className="font-medium">{t.name}</TableCell>
                    <TableCell>
                      <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${trendBadge(t.momentum)}`}>
                        {t.momentum || "N/A"}
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
            Key Actors
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <Skeleton className="h-32 w-full" />
          ) : !actors?.items?.length ? (
            <p className="text-sm text-muted-foreground">Run analysis to identify actors.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Country</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {actors.items.map((a) => (
                  <TableRow key={a.id}>
                    <TableCell className="font-medium">{a.name}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{a.actor_type || "N/A"}</Badge>
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
            Opportunities
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <Skeleton className="h-32 w-full" />
          ) : !opportunities?.items?.length ? (
            <p className="text-sm text-muted-foreground">Run analysis to detect opportunities.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Title</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Priority</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {opportunities.items.map((o) => (
                  <TableRow key={o.id}>
                    <TableCell className="font-medium">{o.title}</TableCell>
                    <TableCell>
                      <Badge variant="secondary">{o.opportunity_type || "N/A"}</Badge>
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
