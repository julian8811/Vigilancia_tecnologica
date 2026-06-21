"use client";

import { useParams } from "next/navigation";
import { useState } from "react";
import { useProject } from "@/hooks/use-projects";
import { useReports, useGenerateReport } from "@/hooks/use-analysis";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
  FileBarChart,
  Loader2,
  FileDown,
  FileText,
  FileCode2,
  Trash2,
  Play,
} from "lucide-react";
import { toast } from "sonner";
import { format } from "date-fns";
import { es } from "date-fns/locale";

export default function ReportsPage() {
  const params = useParams();
  const projectId = params.id as string;
  const { data: project } = useProject(projectId);
  const { data: reportsData, isLoading } = useReports(projectId);
  const generateReport = useGenerateReport();
  const [title, setTitle] = useState("");
  const [reportType, setReportType] = useState("complete");

  const handleGenerate = async () => {
    const reportTitle = title || `Report - ${project?.name || projectId}`;
    try {
      await generateReport.mutateAsync({
        projectId,
        title: reportTitle,
        reportType,
      });
      toast.success("Report generated");
      setTitle("");
    } catch (err: any) {
      toast.error(err?.detail || "Failed to generate report");
    }
  };

  const statusVariant = (status: string) => {
    switch (status) {
      case "completed": return "graph_ready" as const;
      case "failed": return "destructive" as const;
      case "generating": return "processing" as const;
      default: return "outline" as const;
    }
  };

  return (
    <div className="space-y-6">
      {/* Generate Report */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileBarChart className="h-5 w-5" />
            Generate Report
          </CardTitle>
          <CardDescription>
            Create a surveillance report from your project data and analysis.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex gap-3">
            <Input
              placeholder="Report title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="flex-1"
            />
            <Select value={reportType} onValueChange={setReportType}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Report type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="complete">Complete</SelectItem>
                <SelectItem value="executive">Executive</SelectItem>
                <SelectItem value="academic">Academic</SelectItem>
                <SelectItem value="business">Business</SelectItem>
              </SelectContent>
            </Select>
            <Button
              onClick={handleGenerate}
              disabled={generateReport.isPending}
            >
              {generateReport.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Play className="mr-2 h-4 w-4" />
              )}
              Generate
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Reports list */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Generated Reports</CardTitle>
          <CardDescription>
            Download and manage your surveillance reports.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : !reportsData?.items?.length ? (
            <div className="py-12 text-center">
              <FileBarChart className="mx-auto h-12 w-12 text-muted-foreground/50" />
              <p className="mt-4 text-sm text-muted-foreground">
                No reports yet. Click &quot;Generate&quot; to create one.
              </p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Title</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Generated</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {reportsData.items.map((report) => (
                  <TableRow key={report.id}>
                    <TableCell className="font-medium">
                      {report.title}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{report.report_type}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant={statusVariant(report.status)}>
                        {report.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {report.generated_at
                        ? format(new Date(report.generated_at), "PP", { locale: es })
                        : "-"}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        {report.html_path && (
                          <Button variant="ghost" size="icon" asChild title="View HTML">
                            <a
                              href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/projects/${projectId}/reports/${report.id}/download/html`}
                              target="_blank"
                            >
                              <FileText className="h-4 w-4" />
                            </a>
                          </Button>
                        )}
                        {report.pdf_path && (
                          <Button variant="ghost" size="icon" asChild title="Download PDF">
                            <a
                              href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/projects/${projectId}/reports/${report.id}/download/pdf`}
                              download
                            >
                              <FileDown className="h-4 w-4" />
                            </a>
                          </Button>
                        )}
                        {report.markdown_path && (
                          <Button variant="ghost" size="icon" asChild title="Download Markdown">
                            <a
                              href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/projects/${projectId}/reports/${report.id}/download/markdown`}
                              download
                            >
                              <FileCode2 className="h-4 w-4" />
                            </a>
                          </Button>
                        )}
                      </div>
                    </TableCell>
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
