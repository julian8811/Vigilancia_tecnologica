"use client";

import { useState, useRef } from "react";
import { useParams } from "next/navigation";
import {
  useDocuments,
  useUploadDocument,
  useAddUrlDocument,
  useDeleteDocument,
  useReprocessDocument,
} from "@/hooks/use-documents";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
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
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
  Upload,
  Link,
  FileText,
  Trash2,
  RefreshCw,
  Loader2,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { toast } from "sonner";
import { format } from "date-fns";
import { es } from "date-fns/locale";

const statusLabels: Record<string, string> = {
  pending: "Pending",
  processing: "Processing",
  ready: "Ready",
  error: "Error",
};

const statusVariants: Record<string, any> = {
  pending: "outline",
  processing: "processing",
  ready: "graph_ready",
  error: "destructive",
};

const sourceLabels: Record<string, string> = {
  manual_upload: "Uploaded",
  openalex: "OpenAlex",
};

function SourceBadge({ sourceName }: { sourceName?: string }) {
  if (!sourceName || sourceName === "manual_upload") {
    return <span className="text-xs text-muted-foreground">Manual</span>;
  }
  return (
    <Badge
      variant={sourceName === "openalex" ? "graph_ready" : "outline"}
      className="text-[10px] px-1.5 py-0"
    >
      {sourceLabels[sourceName] || sourceName}
    </Badge>
  );
}

export default function DocumentsPage() {
  const params = useParams();
  const projectId = params.id as string;
  const [page, setPage] = useState(1);
  const [url, setUrl] = useState("");
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { data, isLoading } = useDocuments(projectId, page, 20);
  const uploadDocument = useUploadDocument();
  const addUrlDocument = useAddUrlDocument();
  const deleteDocument = useDeleteDocument();
  const reprocessDocument = useReprocessDocument();

  const documents = data?.items || [];
  const totalPages = data?.total_pages || 1;

  // File upload
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      await uploadDocument.mutateAsync({ projectId, file });
      toast.success("Document uploaded");
    } catch (err: any) {
      toast.error(err?.message || "Upload failed");
    }
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  // URL upload
  const handleUrlAdd = async () => {
    if (!url.trim()) return;
    try {
      await addUrlDocument.mutateAsync({ project_id: projectId, url: url.trim() });
      toast.success("URL added");
      setUrl("");
    } catch (err: any) {
      toast.error(err?.detail || "Failed to add URL");
    }
  };

  // Delete
  const handleDelete = async () => {
    if (!deleteId) return;
    try {
      await deleteDocument.mutateAsync({ projectId, docId: deleteId });
      toast.success("Document deleted");
      setDeleteId(null);
    } catch (err: any) {
      toast.error(err?.detail || "Failed to delete document");
    }
  };

  // Reprocess
  const handleReprocess = async (id: string) => {
    try {
      await reprocessDocument.mutateAsync({ projectId, docId: id });
      toast.success("Document queued for reprocessing");
    } catch (err: any) {
      toast.error(err?.detail || "Failed to reprocess document");
    }
  };

  return (
    <div className="space-y-6">
      {/* Upload area */}
      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              <Upload className="h-4 w-4" />
              Upload File
            </CardTitle>
            <CardDescription>
              Upload a patent PDF, scientific paper, or document.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <Input
                ref={fileInputRef}
                type="file"
                className="text-sm"
                onChange={handleFileUpload}
                disabled={uploadDocument.isPending}
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              <Link className="h-4 w-4" />
              Add URL
            </CardTitle>
            <CardDescription>
              Add a news article, blog post, or online resource.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <Input
                placeholder="https://..."
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleUrlAdd()}
              />
              <Button
                size="sm"
                onClick={handleUrlAdd}
                disabled={addUrlDocument.isPending || !url.trim()}
              >
                {addUrlDocument.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  "Add"
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Documents table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Documents</CardTitle>
          <CardDescription>
            {data?.total ?? 0} document{(data?.total ?? 0) !== 1 ? "s" : ""} total
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : documents.length === 0 ? (
            <div className="py-8 text-center text-sm text-muted-foreground">
              No documents yet. Upload a file or add a URL to get started.
            </div>
          ) : (
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Title</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Source</TableHead>
                    <TableHead>Uploaded</TableHead>
                    <TableHead className="w-[120px]"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {documents.map((doc) => (
                    <TableRow key={doc.id}>
                      <TableCell className="font-medium">
                        <div className="flex items-center gap-2">
                          <FileText className="h-4 w-4 text-muted-foreground" />
                          <span className="max-w-xs truncate">
                            {doc.title}
                          </span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className="uppercase text-xs">
                          {doc.file_type}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            statusVariants[doc.processing_status] || "outline"
                          }
                        >
                          {statusLabels[doc.processing_status] ||
                            doc.processing_status}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <SourceBadge sourceName={doc.source_name} />
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {format(new Date(doc.created_at), "PP", { locale: es })}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleReprocess(doc.id)}
                            title="Reprocess"
                            disabled={reprocessDocument.isPending}
                          >
                            <RefreshCw className="h-4 w-4" />
                          </Button>
                          <AlertDialog>
                            <AlertDialogTrigger asChild>
                              <Button
                                variant="ghost"
                                size="icon"
                                className="text-destructive"
                                onClick={() => setDeleteId(doc.id)}
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </AlertDialogTrigger>
                          </AlertDialog>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="mt-4 flex items-center justify-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
              >
                <ChevronLeft className="h-4 w-4" />
                Previous
              </Button>
              <span className="text-sm text-muted-foreground">
                Page {page} of {totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
              >
                Next
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Delete confirmation */}
      <AlertDialog
        open={!!deleteId}
        onOpenChange={(open) => !open && setDeleteId(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete document?</AlertDialogTitle>
            <AlertDialogDescription>
              This action cannot be undone. The document will be permanently
              removed.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
