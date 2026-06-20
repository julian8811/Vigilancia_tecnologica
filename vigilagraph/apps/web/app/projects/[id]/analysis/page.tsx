"use client";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { BarChart3 } from "lucide-react";

export default function AnalysisPage() {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <BarChart3 className="h-5 w-5" />
          Analysis
        </CardTitle>
        <CardDescription>
          Deep analysis and insights from your knowledge graph.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="py-12 text-center">
          <BarChart3 className="mx-auto h-12 w-12 text-muted-foreground/50" />
          <p className="mt-4 text-sm text-muted-foreground">
            Analysis features are coming soon. This section will provide
            trend analysis, topic modeling, and anomaly detection.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
