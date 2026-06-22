"use client";

import {
  useEffect,
  useRef,
  useImperativeHandle,
  forwardRef,
  useCallback,
  useState,
} from "react";
import cytoscape from "cytoscape";
import type { GraphNode, GraphEdge } from "@/types/api";
import { elementsToCyData, communityColor, getNodeTypeColor } from "@/lib/graph-utils";
import { Loader2, AlertTriangle } from "lucide-react";

// Dagre availability flag — loaded once via dynamic import
let dagreAvailable = false;

async function ensureDagre() {
  if (typeof window === "undefined") return false;
  try {
    const dagre = await import("cytoscape-dagre");
    cytoscape.use(dagre.default || dagre);
    dagreAvailable = true;
  } catch {
    dagreAvailable = false;
  }
}
ensureDagre();

export interface CytoscapeGraphHandle {
  zoomToNode: (nodeId: string) => void;
  fitToScreen: () => void;
}

interface CytoscapeGraphProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  onNodeSelect: (nodeId: string) => void;
  onNodeDeselect: () => void;
}

export const CytoscapeGraph = forwardRef<
  CytoscapeGraphHandle,
  CytoscapeGraphProps
>(({ nodes, edges, onNodeSelect, onNodeDeselect }, ref) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);
  const [initError, setInitError] = useState<string | null>(null);

  // Expose imperative methods
  useImperativeHandle(ref, () => ({
    zoomToNode(nodeId: string) {
      const cy = cyRef.current;
      if (!cy) return;
      const el = cy.getElementById(nodeId);
      if (el.length) {
        cy.fit(el, 100);
        cy.animate({
          duration: 400,
        } as any);
        cy.nodes().unselect();
        el.select();
      }
    },
    fitToScreen() {
      cyRef.current?.fit(undefined, 50);
    },
  }));

  // Build the graph
  useEffect(() => {
    if (!containerRef.current) return;
    if (!nodes.length && !edges.length) return;

    // Destroy previous instance
    if (cyRef.current) {
      cyRef.current.destroy();
      cyRef.current = null;
    }

    try {
      const elements = elementsToCyData(nodes, edges);

    // Build node type → color map for style
    const nodeTypes = Array.from(new Set(nodes.map((n) => n.node_type)));
    const communities = Array.from(
      new Set(
        nodes
          .map((n) => n.community_id)
          .filter((c): c is number => c !== undefined && c !== null),
      ),
    );

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      style: [
        // Node defaults
        {
          selector: "node",
          style: {
            "background-color": "#6366f1",
            label: "data(label)",
            "font-size": "10px",
            "text-wrap": "wrap",
            "text-max-width": "120px",
            "text-valign": "bottom",
            "text-halign": "center",
            color: "#888",
            "border-width": 0,
            width: "mapData(centrality, 0, 1, 20, 60)",
            height: "mapData(centrality, 0, 1, 20, 60)",
            "transition-property":
              "background-color, border-color, width, height",
            "transition-duration": 200,
          } as any,
        },
        // Node type colors
        ...nodeTypes.map((type) => ({
          selector: `node[nodeType = "${type}"]`,
          style: {
            "background-color": getNodeTypeColor(type),
          } as any,
        })),
        // Community border colors
        ...communities.map((c) => ({
          selector: `node[community = ${c}]`,
          style: {
            "border-color": communityColor(c),
            "border-width": 3,
            "border-opacity": 0.6,
          } as any,
        })),
        // Edge defaults
        {
          selector: "edge",
          style: {
            width: "mapData(weight, 0, 1, 1, 4)",
            "line-color": "#555",
            "target-arrow-color": "#555",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            opacity: 0.6,
          } as any,
        },
        // Selected node
        {
          selector: "node:selected",
          style: {
            "border-width": 4,
            "border-color": "#fff",
            "shadow-blur": 20,
            "shadow-color": "#fff",
            "shadow-opacity": 0.5,
          } as any,
        },
        // Selected edge
        {
          selector: "edge:selected",
          style: {
            "line-color": "#fff",
            "target-arrow-color": "#fff",
            width: 3,
            opacity: 1,
          } as any,
        },
      ],
      layout: {
        name: dagreAvailable ? "dagre" : "cose",
        animate: true,
        animationDuration: 500,
        ...(dagreAvailable
          ? {
              rankDir: "LR",
              spacingFactor: 1.5,
              nodeSep: 60,
              rankSep: 100,
            }
          : {
              nodeRepulsion: () => 8000,
              idealEdgeLength: () => 120,
              gravity: 0.3,
            }),
      } as any,
      wheelSensitivity: 0.3,
      minZoom: 0.1,
      maxZoom: 4,
    });

    cyRef.current = cy;

    // Node click handler
    cy.on("tap", "node", (evt) => {
      const nodeId = evt.target.id();
      onNodeSelect(nodeId);
    });

    // Background click → deselect
    cy.on("tap", (evt) => {
      if (evt.target === cy) {
        cy.nodes().unselect();
        onNodeDeselect();
      }
    });

    return () => {
      cy.destroy();
      cyRef.current = null;
    };
    } catch (err: any) {
      console.error("Cytoscape init error:", err);
      setInitError(err?.message || "Error al inicializar el grafo");
    }
  }, [nodes, edges, onNodeSelect, onNodeDeselect]);

  if (initError) {
    return (
      <div className="flex h-full w-full items-center justify-center" style={{ minHeight: "400px" }}>
        <div className="flex flex-col items-center gap-3 text-center p-6">
          <AlertTriangle className="h-8 w-8 text-destructive" />
          <p className="font-medium text-sm">Error al renderizar el grafo</p>
          <p className="text-xs text-muted-foreground">{initError}</p>
        </div>
      </div>
    );
  }

  if (!nodes.length && !edges.length) {
    return (
      <div className="flex h-full w-full items-center justify-center" style={{ minHeight: "400px" }}>
        <div className="flex flex-col items-center gap-3 text-center p-6">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Cargando grafo...</p>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="h-full w-full"
      style={{ minHeight: "400px" }}
    />
  );
});

CytoscapeGraph.displayName = "CytoscapeGraph";
