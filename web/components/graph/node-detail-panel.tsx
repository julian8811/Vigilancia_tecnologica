"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { X, Search, ExternalLink } from "lucide-react";
import type { GraphNode, GraphEdge } from "@/types/api";
import { communityColor, getNodeTypeColor } from "@/lib/graph-utils";

interface NodeDetailPanelProps {
  node: GraphNode;
  onClose: () => void;
  onZoomToNode: (nodeId: string) => void;
  allNodes: GraphNode[];
  allEdges: GraphEdge[];
}

export function NodeDetailPanel({
  node,
  onClose,
  onZoomToNode,
  allNodes,
  allEdges,
}: NodeDetailPanelProps) {
  // Find connected nodes
  const connectedEdges = allEdges.filter(
    (e) =>
      e.source_node_id === (node.external_node_id || node.id) ||
      e.target_node_id === (node.external_node_id || node.id),
  );

  const connectedNodeIds = new Set<string>();
  connectedEdges.forEach((e) => {
    if (e.source_node_id !== (node.external_node_id || node.id))
      connectedNodeIds.add(e.source_node_id);
    if (e.target_node_id !== (node.external_node_id || node.id))
      connectedNodeIds.add(e.target_node_id);
  });

  const connectedNodes = allNodes.filter((n) =>
    connectedNodeIds.has(n.external_node_id || n.id),
  );

  const metadataEntries = node.metadata_json
    ? Object.entries(node.metadata_json).filter(
        ([, v]) => v !== null && v !== undefined,
      )
    : [];

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b px-4 py-3">
        <h3 className="text-sm font-semibold">Detalles del nodo</h3>
        <Button variant="ghost" size="icon" onClick={onClose}>
          <X className="h-4 w-4" />
        </Button>
      </div>

      <ScrollArea className="flex-1 p-4">
        <div className="space-y-4">
          {/* Node label */}
          <div>
            <p className="text-xs text-muted-foreground">Etiqueta</p>
            <p className="text-sm font-medium">{node.label}</p>
          </div>

          {/* Node ID */}
          <div>
            <p className="text-xs text-muted-foreground">ID del nodo</p>
            <p className="text-sm font-mono">{node.external_node_id || node.id}</p>
          </div>

          {/* Type */}
          <div>
            <p className="text-xs text-muted-foreground">Tipo</p>
            <Badge
              className="mt-1"
              style={{
                backgroundColor: getNodeTypeColor(node.node_type),
                color: "#fff",
              }}
            >
              {node.node_type}
            </Badge>
          </div>

          {/* Community */}
          {node.community_id !== undefined && node.community_id !== null && (
            <div>
              <p className="text-xs text-muted-foreground">Comunidad</p>
              <Badge
                className="mt-1"
                style={{
                  backgroundColor: communityColor(node.community_id),
                  color: "#fff",
                }}
              >
                {node.community_id}
              </Badge>
            </div>
          )}

          {/* Centrality */}
          {node.centrality_score !== undefined && node.centrality_score !== null && (
            <div>
              <p className="text-xs text-muted-foreground">Centralidad</p>
              <p className="text-sm font-medium">
                {node.centrality_score.toFixed(4)}
              </p>
            </div>
          )}

          {/* Zoom to node */}
          <Button
            variant="outline"
            size="sm"
            className="w-full"
            onClick={() => onZoomToNode(node.external_node_id || node.id)}
          >
            <Search className="mr-2 h-4 w-4" />
            Acercar al nodo
          </Button>
        </div>

        {/* Connected nodes */}
        {connectedNodes.length > 0 && (
          <div className="mt-6 space-y-2">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Nodos conectados ({connectedNodes.length})
            </p>
            <div className="space-y-1">
              {connectedNodes.slice(0, 20).map((cn) => (
                <button
                  key={cn.id}
                  className="flex w-full items-center gap-2 rounded px-2 py-1 text-left text-sm hover:bg-accent"
                  onClick={() => onZoomToNode(cn.external_node_id || cn.id)}
                >
                  <span
                    className="h-2 w-2 rounded-full shrink-0"
                    style={{
                      backgroundColor: getNodeTypeColor(cn.node_type),
                    }}
                  />
                  <span className="truncate flex-1">{cn.label}</span>
                  <ExternalLink className="h-3 w-3 shrink-0 text-muted-foreground" />
                </button>
              ))}
              {connectedNodes.length > 20 && (
                <p className="text-xs text-muted-foreground">
                  +{connectedNodes.length - 20} más
                </p>
              )}
            </div>
          </div>
        )}

        {/* Metadata */}
        {metadataEntries.length > 0 && (
          <div className="mt-6 space-y-2">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Metadatos
            </p>
            <div className="space-y-1">
              {metadataEntries.map(([key, value]) => (
                <div key={key} className="text-sm">
                  <span className="text-muted-foreground">{key}: </span>
                  <span>
                    {typeof value === "object"
                      ? JSON.stringify(value)
                      : String(value)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </ScrollArea>
    </div>
  );
}
