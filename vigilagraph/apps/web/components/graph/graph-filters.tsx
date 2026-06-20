"use client";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Search } from "lucide-react";

interface GraphFiltersProps {
  search: string;
  onSearchChange: (value: string) => void;
  nodeTypes: string[];
  selectedTypes: string[];
  onTypesChange: (types: string[]) => void;
  communities: number[];
  selectedCommunities: number[];
  onCommunitiesChange: (communities: number[]) => void;
}

export function GraphFilters({
  search,
  onSearchChange,
  nodeTypes,
  selectedTypes,
  onTypesChange,
  communities,
  selectedCommunities,
  onCommunitiesChange,
}: GraphFiltersProps) {
  const toggleType = (type: string) => {
    onTypesChange(
      selectedTypes.includes(type)
        ? selectedTypes.filter((t) => t !== type)
        : [...selectedTypes, type],
    );
  };

  const toggleCommunity = (community: number) => {
    onCommunitiesChange(
      selectedCommunities.includes(community)
        ? selectedCommunities.filter((c) => c !== community)
        : [...selectedCommunities, community],
    );
  };

  return (
    <div className="space-y-4">
      {/* Search */}
      <div className="space-y-2">
        <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
          Search
        </Label>
        <div className="relative">
          <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Filter by label..."
            className="pl-8 h-9 text-sm"
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
          />
        </div>
      </div>

      {/* Node types */}
      {nodeTypes.length > 0 && (
        <div className="space-y-2">
          <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
            Node Type
          </Label>
          <div className="space-y-1">
            {nodeTypes.map((type) => (
              <label
                key={type}
                className="flex items-center gap-2 cursor-pointer text-sm hover:text-foreground"
              >
                <input
                  type="checkbox"
                  className="rounded border-gray-600"
                  checked={
                    selectedTypes.length === 0 ||
                    selectedTypes.includes(type)
                  }
                  onChange={() => toggleType(type)}
                />
                <span className="capitalize">{type}</span>
              </label>
            ))}
          </div>
        </div>
      )}

      {/* Communities */}
      {communities.length > 0 && (
        <div className="space-y-2">
          <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
            Communities
          </Label>
          <div className="space-y-1">
            {communities.map((c) => (
              <label
                key={c}
                className="flex items-center gap-2 cursor-pointer text-sm hover:text-foreground"
              >
                <input
                  type="checkbox"
                  className="rounded border-gray-600"
                  checked={
                    selectedCommunities.length === 0 ||
                    selectedCommunities.includes(c)
                  }
                  onChange={() => toggleCommunity(c)}
                />
                <span>Community {c}</span>
              </label>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
