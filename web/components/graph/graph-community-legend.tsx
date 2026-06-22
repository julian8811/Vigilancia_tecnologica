"use client";

import { communityColor } from "@/lib/graph-utils";

interface GraphCommunityLegendProps {
  communities: number[];
  selectedCommunities: number[];
  onToggle: (community: number) => void;
}

export function GraphCommunityLegend({
  communities,
  selectedCommunities,
  onToggle,
}: GraphCommunityLegendProps) {
  if (communities.length === 0) return null;

  const allSelected = selectedCommunities.length === 0;

  return (
    <div className="space-y-2">
      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
        Comunidades
      </p>
      <div className="space-y-1.5">
        {communities.map((c) => {
          const color = communityColor(c);
          const active = allSelected || selectedCommunities.includes(c);
          return (
            <button
              key={c}
              className={`flex w-full items-center gap-2 rounded px-2 py-1 text-left text-sm transition-colors hover:bg-accent ${
                active ? "opacity-100" : "opacity-40"
              }`}
              onClick={() => onToggle(c)}
            >
              <span
                className="h-3 w-3 rounded-sm shrink-0"
                style={{ backgroundColor: color }}
              />
              <span>Comunidad {c}</span>
              {!active && <span className="ml-auto text-xs">oculta</span>}
            </button>
          );
        })}
      </div>
    </div>
  );
}
