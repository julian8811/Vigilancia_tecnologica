"use client";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { FileBarChart } from "lucide-react";

export default function ReportsPage() {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileBarChart className="h-5 w-5" />
          Reports
        </CardTitle>
        <CardDescription>
          Generate and manage surveillance reports.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="py-12 text-center">
          <FileBarChart className="mx-auto h-12 w-12 text-muted-foreground/50" />
          <p className="mt-4 text-sm text-muted-foreground">
            Reports are coming soon. This section will provide downloadable
            PDF and HTML reports with insights from your graph.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
