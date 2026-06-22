"use client";

import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Maximize2, ZoomIn, ZoomOut } from "lucide-react";

interface GraphLayoutProps {
  layout: string;
  onLayoutChange: (layout: string) => void;
  onFit: () => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
}

const layouts = [
  { value: "dagre", label: "Hierarchical (dagre)" },
  { value: "cose", label: "Force-directed (cose)" },
  { value: "concentric", label: "Concentric" },
  { value: "breadthfirst", label: "Breadth-first" },
];

export function GraphLayout({
  layout,
  onLayoutChange,
  onFit,
  onZoomIn,
  onZoomOut,
}: GraphLayoutProps) {
  return (
    <div className="flex items-center gap-2">
      <Select value={layout} onValueChange={onLayoutChange}>
        <SelectTrigger className="h-8 w-40 text-xs">
          <SelectValue placeholder="Layout" />
        </SelectTrigger>
        <SelectContent>
          {layouts.map((l) => (
            <SelectItem key={l.value} value={l.value} className="text-xs">
              {l.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Button variant="outline" size="icon" onClick={onZoomIn} title="Zoom in">
        <ZoomIn className="h-4 w-4" />
      </Button>
      <Button
        variant="outline"
        size="icon"
        onClick={onZoomOut}
        title="Zoom out"
      >
        <ZoomOut className="h-4 w-4" />
      </Button>
      <Button
        variant="outline"
        size="icon"
        onClick={onFit}
        title="Fit to screen"
      >
        <Maximize2 className="h-4 w-4" />
      </Button>
    </div>
  );
}
