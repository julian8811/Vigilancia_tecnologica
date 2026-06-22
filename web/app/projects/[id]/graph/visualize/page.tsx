"use client";

import { useState, useCallback, useRef } from "react";
import { useParams } from "next/navigation";
import { useLatestRun } from "@/hooks/use-graph";
import { useGraphData } from "@/hooks/use-graph-data";
import { CytoscapeGraph, type CytoscapeGraphHandle } from "@/components/graph/cytoscape-graph";
import { GraphFilters } from "@/components/graph/graph-filters";
import { NodeDetailPanel } from "@/components/graph/node-detail-panel";
import { GraphCommunityLegend } from "@/components/graph/graph-community-legend";
import { GraphLayout } from "@/components/graph/graph-layout";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Loader2, AlertTriangle } from "lucide-react";
import Link from "next/link";
import type { GraphNode } from "@/types/api";
import { filterNodes } from "@/lib/graph-utils";

export default function GraphVisualizePage() {
  const params = useParams();
  const projectId = params.id as string;
  const graphRef = useRef<CytoscapeGraphHandle>(null);

  const { data: latestRun, isLoading: runLoading } = useLatestRun(projectId);
  const {
    nodes: allNodes,
    edges: allEdges,
    loading: dataLoading,
    error: dataError,
  } = useGraphData(projectId, latestRun?.id);

  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [search, setSearch] = useState("");
  const [selectedTypes, setSelectedTypes] = useState<string[]>([]);
  const [selectedCommunities, setSelectedCommunities] = useState<number[]>([]);

  // Get unique node types and communities
  const nodeTypes = Array.from(new Set(allNodes.map((n) => n.node_type)));
  const communities = Array.from(
    new Set(
      allNodes
        .map((n) => n.community_id)
        .filter((c): c is number => c !== undefined && c !== null),
    ),
  );

  // Filtered data
  const filteredNodes = filterNodes(allNodes, {
    search,
    types: selectedTypes.length > 0 ? selectedTypes : undefined,
    communities: selectedCommunities.length > 0 ? selectedCommunities : undefined,
  });

  const filteredNodeIds = new Set(filteredNodes.map((n) => n.external_node_id || n.id));
  const filteredEdges = allEdges.filter(
    (e) =>
      filteredNodeIds.has(e.source_node_id) &&
      filteredNodeIds.has(e.target_node_id),
  );

  const handleNodeSelect = useCallback(
    (nodeId: string) => {
      const node = allNodes.find(
        (n) => n.external_node_id === nodeId || n.id === nodeId,
      );
      setSelectedNode(node || null);
    },
    [allNodes],
  );

  const handleNodeDeselect = useCallback(() => {
    setSelectedNode(null);
  }, []);

  const handleZoomToNode = useCallback((nodeId: string) => {
    graphRef.current?.zoomToNode(nodeId);
  }, []);

  const loading = runLoading || dataLoading;

  if (loading) {
    return (
      <div className="flex h-[calc(100vh-8rem)] items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Cargando datos del grafo...</p>
        </div>
      </div>
    );
  }

  if (dataError) {
    return (
      <div className="flex h-[calc(100vh-8rem)] items-center justify-center">
        <div className="flex flex-col items-center gap-3 text-center">
          <AlertTriangle className="h-8 w-8 text-destructive" />
          <p className="font-medium">Error al cargar el grafo</p>
          <p className="text-sm text-muted-foreground">
            {dataError.message}
          </p>
          <Button variant="outline" asChild>
            <Link href={`/projects/${projectId}/graph`}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              Volver al grafo
            </Link>
          </Button>
        </div>
      </div>
    );
  }

  if (!latestRun || allNodes.length === 0) {
    return (
      <div className="flex h-[calc(100vh-8rem)] items-center justify-center">
        <div className="flex flex-col items-center gap-3 text-center">
          <p className="font-medium">No hay datos del grafo disponibles</p>
          <p className="text-sm text-muted-foreground">
            Generá un grafo primero desde la pestaña Grafo.
          </p>
          <Button variant="outline" asChild>
            <Link href={`/projects/${projectId}/graph`}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              Volver al grafo
            </Link>
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100vh-8rem)] -m-4 lg:-m-6">
      {/* Left sidebar — filters */}
      <div className="w-64 shrink-0 overflow-y-auto border-r bg-card p-4">
        <div className="mb-4">
          <Button variant="ghost" size="sm" asChild>
            <Link href={`/projects/${projectId}/graph`}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              Volver
            </Link>
          </Button>
        </div>
        <div className="space-y-6">
          <div>
            <p className="mb-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Nodos
            </p>
            <p className="text-lg font-bold">{allNodes.length}</p>
          </div>
          <div>
            <p className="mb-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Aristas
            </p>
            <p className="text-lg font-bold">{allEdges.length}</p>
          </div>

          <GraphFilters
            search={search}
            onSearchChange={setSearch}
            nodeTypes={nodeTypes}
            selectedTypes={selectedTypes}
            onTypesChange={setSelectedTypes}
            communities={communities}
            selectedCommunities={selectedCommunities}
            onCommunitiesChange={setSelectedCommunities}
          />

          <GraphCommunityLegend
            communities={communities}
            selectedCommunities={selectedCommunities}
            onToggle={(c) => {
              setSelectedCommunities((prev) =>
                prev.includes(c)
                  ? prev.filter((x) => x !== c)
                  : [...prev, c],
              );
            }}
          />
        </div>
      </div>

      {/* Graph canvas */}
      <div className="flex-1 relative">
        <CytoscapeGraph
          ref={graphRef}
          nodes={filteredNodes}
          edges={filteredEdges}
          onNodeSelect={handleNodeSelect}
          onNodeDeselect={handleNodeDeselect}
        />
      </div>

      {/* Right sidebar — node details */}
      {selectedNode && (
        <div className="w-80 shrink-0 overflow-y-auto border-l bg-card">
          <NodeDetailPanel
            node={selectedNode}
            onClose={() => setSelectedNode(null)}
            onZoomToNode={handleZoomToNode}
            allNodes={allNodes}
            allEdges={allEdges}
          />
        </div>
      )}
    </div>
  );
}
