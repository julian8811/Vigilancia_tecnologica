"use client";

import { useParams } from "next/navigation";
import { useState } from "react";
import { useSearchStrategy, useProject } from "@/hooks/use-projects";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Search,
  Loader2,
  Database,
  Download,
  Eye,
  FileText,
  Brain,
} from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";

interface SearchResult {
  title: string;
  authors: string[];
  year: number | null;
  doi: string | null;
  source: string;
  relevance: number;
}

export default function SearchPage() {
  const params = useParams();
  const projectId = params.id as string;
  const { data: project } = useProject(projectId);
  const { data: strategy } = useSearchStrategy(projectId);
  const [query, setQuery] = useState(strategy?.boolean_queries || strategy?.keywords_en || "");
  const [source, setSource] = useState("openalex");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [searched, setSearched] = useState(false);
  const [selectedDois, setSelectedDois] = useState<Set<string>>(new Set());
  const [importing, setImporting] = useState(false);

  const handleSearch = async () => {
    if (!query.trim()) {
      toast.error("Enter a search query");
      return;
    }
    setSearching(true);
    setSearched(true);
    try {
      const data = await api.post<{ results: SearchResult[] }>("/search/preview", {
        query: query.trim(),
        source,
        project_id: projectId,
      });
      setResults(data.results || []);
      setSelectedDois(new Set());
    } catch (err: any) {
      toast.error(err?.detail || "Search failed");
      setResults([]);
    } finally {
      setSearching(false);
    }
  };

  const toggleResult = (doi: string) => {
    const next = new Set(selectedDois);
    if (next.has(doi)) next.delete(doi);
    else next.add(doi);
    setSelectedDois(next);
  };

  const handleImport = async () => {
    if (selectedDois.size === 0) {
      toast.error("Select at least one result to import");
      return;
    }
    setImporting(true);
    try {
      await api.post(`/projects/${projectId}/collect-from-search`, {
        results: results.filter((r) => selectedDois.has(r.doi || r.title)),
        source,
      });
      toast.success(`Imported ${selectedDois.size} documents`);
      setSelectedDois(new Set());
    } catch (err: any) {
      toast.error(err?.detail || "Import failed");
    } finally {
      setImporting(false);
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Search className="h-5 w-5" />
            Search & Collect
          </CardTitle>
          <CardDescription>
            Search external sources by keywords or boolean equations, preview
            results, and import selected documents to your project.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Query builder */}
          <div className="space-y-2">
            <label className="text-sm font-medium">
              Search query (keywords or boolean)
            </label>
            <Textarea
              placeholder={`Examples:\n- quantum computing OR machine learning\n- "biological control" AND Colombia\n- artificial intelligence AND agriculture`}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              rows={3}
            />
            <p className="text-xs text-muted-foreground">
              Use AND, OR, NOT operators. Quotes for exact phrases.
            </p>
          </div>

          {/* Source selector + search button */}
          <div className="flex gap-3">
            <Select value={source} onValueChange={setSource}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Source" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="openalex">OpenAlex</SelectItem>
                <SelectItem value="semantic_scholar">Semantic Scholar</SelectItem>
                <SelectItem value="lens">Lens.org (patents)</SelectItem>
              </SelectContent>
            </Select>
            <Button onClick={handleSearch} disabled={searching} className="flex-1">
              {searching ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Search className="mr-2 h-4 w-4" />
              )}
              Search
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Results */}
      {searching && (
        <Card>
          <CardContent className="py-8 text-center">
            <Loader2 className="mx-auto h-8 w-8 animate-spin text-muted-foreground" />
            <p className="mt-2 text-sm text-muted-foreground">Searching...</p>
          </CardContent>
        </Card>
      )}

      {!searching && searched && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span className="flex items-center gap-2">
                <Database className="h-5 w-5" />
                Results ({results.length})
              </span>
              {results.length > 0 && (
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() =>
                      setSelectedDois(new Set(results.map((r) => r.doi || r.title)))
                    }
                  >
                    Select All
                  </Button>
                  <Button
                    size="sm"
                    onClick={handleImport}
                    disabled={importing || selectedDois.size === 0}
                  >
                    {importing ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Download className="mr-2 h-4 w-4" />
                    )}
                    Import ({selectedDois.size})
                  </Button>
                </div>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {results.length === 0 ? (
              <div className="py-12 text-center">
                <Search className="mx-auto h-12 w-12 text-muted-foreground/50" />
                <p className="mt-4 text-sm text-muted-foreground">
                  No results found. Try broader keywords or a different source.
                </p>
              </div>
            ) : (
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-10"></TableHead>
                      <TableHead>Title</TableHead>
                      <TableHead>Authors</TableHead>
                      <TableHead>Year</TableHead>
                      <TableHead>Source</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {results.map((r, i) => {
                      const key = r.doi || r.title + i;
                      return (
                        <TableRow
                          key={key}
                          className={
                            selectedDois.has(key) ? "bg-primary/5" : ""
                          }
                        >
                          <TableCell>
                            <input
                              type="checkbox"
                              checked={selectedDois.has(key)}
                              onChange={() => toggleResult(key)}
                              className="h-4 w-4"
                            />
                          </TableCell>
                          <TableCell className="font-medium max-w-md truncate">
                            {r.title}
                          </TableCell>
                          <TableCell className="text-sm text-muted-foreground max-w-xs truncate">
                            {r.authors?.slice(0, 3).join(", ") || "-"}
                          </TableCell>
                          <TableCell>{r.year || "-"}</TableCell>
                          <TableCell>
                            <Badge variant="outline">{r.source}</Badge>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Saved strategy */}
      {strategy && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              <Brain className="h-4 w-4" />
              Current Search Strategy
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            <p>
              <span className="font-medium">Keywords EN:</span>{" "}
              {strategy.keywords_en || "-"}
            </p>
            <p>
              <span className="font-medium">Keywords ES:</span>{" "}
              {strategy.keywords_es || "-"}
            </p>
            {strategy.boolean_queries && (
              <p>
                <span className="font-medium">Boolean:</span>{" "}
                {strategy.boolean_queries}
              </p>
            )}
            <p>
              <span className="font-medium">Sources:</span>{" "}
              {strategy.sources_selected || "-"}
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
