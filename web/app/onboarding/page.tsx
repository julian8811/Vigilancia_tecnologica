"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { useAuth } from "@/hooks/use-auth";
import { useProjects, useCreateProject } from "@/hooks/use-projects";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { BarChart3, Loader2, ArrowRight, Check, Sparkles } from "lucide-react";

const projectSchema = z.object({
  name: z.string().min(1, "Project name is required").max(200),
  topic: z.string().min(1, "Research topic is required").max(500),
  description: z.string().max(2000).optional(),
  surveillance_type: z.enum(["tecnologica", "cientifica", "competitiva", "estrategica"]),
});

type ProjectForm = z.infer<typeof projectSchema>;

const STEPS = ["welcome", "create", "done"] as const;
type Step = (typeof STEPS)[number];

export default function OnboardingPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const { data: projectsData } = useProjects(1, 1);
  const createProject = useCreateProject();
  const [step, setStep] = useState<Step>("welcome");

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<ProjectForm>({
    resolver: zodResolver(projectSchema),
    defaultValues: {
      surveillance_type: "tecnologica",
    },
  });

  const surveillanceType = watch("surveillance_type");

  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login");
      return;
    }
    if (projectsData && projectsData.total > 0) {
      router.push("/dashboard");
    }
  }, [user, authLoading, projectsData, router]);

  if (authLoading || !user) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  const onSubmit = async (data: ProjectForm) => {
    try {
      await createProject.mutateAsync({
        name: data.name,
        topic: data.topic,
        description: data.description || undefined,
        surveillance_type: data.surveillance_type,
        language: "en",
      });
      setStep("done");
    } catch (err: any) {
      toast.error(err?.detail || "Failed to create project");
    }
  };

  const goToProject = () => {
    router.push("/dashboard");
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/30 p-4">
      {step === "welcome" && (
        <Card className="w-full max-w-lg text-center">
          <CardHeader className="space-y-4">
            <div className="flex justify-center">
              <BarChart3 className="h-12 w-12 text-primary" />
            </div>
            <CardTitle className="text-3xl">Welcome to VigilaGraph</CardTitle>
            <CardDescription className="text-base">
              AI-powered technology surveillance. Create your first project
              to start monitoring research trends, technologies, and opportunities.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 text-left text-sm text-muted-foreground">
            <div className="flex items-start gap-3">
              <Sparkles className="mt-0.5 h-5 w-5 shrink-0 text-primary" />
              <div>
                <p className="font-medium text-foreground">Define your topic</p>
                <p>We'll search academic databases and the web for relevant documents.</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <Sparkles className="mt-0.5 h-5 w-5 shrink-0 text-primary" />
              <div>
                <p className="font-medium text-foreground">AI-powered analysis</p>
                <p>Identify technologies, trends, actors, and opportunities automatically.</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <Sparkles className="mt-0.5 h-5 w-5 shrink-0 text-primary" />
              <div>
                <p className="font-medium text-foreground">Knowledge graphs</p>
                <p>Visualize connections between concepts with interactive graphs.</p>
              </div>
            </div>
          </CardContent>
          <CardFooter>
            <Button className="w-full gap-2" size="lg" onClick={() => setStep("create")}>
              Create your first project
              <ArrowRight className="h-4 w-4" />
            </Button>
          </CardFooter>
        </Card>
      )}

      {step === "create" && (
        <Card className="w-full max-w-lg">
          <CardHeader>
            <CardTitle>Create your first project</CardTitle>
            <CardDescription>
              Tell us what you want to research — AI will help with the rest.
            </CardDescription>
          </CardHeader>
          <form onSubmit={handleSubmit(onSubmit)}>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Project name</Label>
                <Input
                  id="name"
                  placeholder="e.g., Biological pest control R&D"
                  {...register("name")}
                />
                {errors.name && (
                  <p className="text-xs text-destructive">{errors.name.message}</p>
                )}
              </div>
              <div className="space-y-2">
                <Label htmlFor="topic">Research topic</Label>
                <Input
                  id="topic"
                  placeholder="e.g., Biological pest control using natural enemies"
                  {...register("topic")}
                />
                {errors.topic && (
                  <p className="text-xs text-destructive">{errors.topic.message}</p>
                )}
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">Description (optional)</Label>
                <Textarea
                  id="description"
                  placeholder="Brief description of your research goals..."
                  rows={3}
                  {...register("description")}
                />
              </div>
              <div className="space-y-2">
                <Label>Surveillance type</Label>
                <Select
                  value={surveillanceType}
                  onValueChange={(v) =>
                    setValue("surveillance_type", v as typeof surveillanceType)
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="tecnologica">Technological</SelectItem>
                    <SelectItem value="cientifica">Scientific</SelectItem>
                    <SelectItem value="competitiva">Competitive</SelectItem>
                    <SelectItem value="estrategica">Strategic</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
            <CardFooter className="flex gap-3">
              <Button
                type="button"
                variant="outline"
                onClick={() => setStep("welcome")}
              >
                Back
              </Button>
              <Button type="submit" className="flex-1 gap-2" disabled={createProject.isPending}>
                {createProject.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Sparkles className="h-4 w-4" />
                )}
                Create project
              </Button>
            </CardFooter>
          </form>
        </Card>
      )}

      {step === "done" && (
        <Card className="w-full max-w-lg text-center">
          <CardHeader className="space-y-4">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
              <Check className="h-8 w-8 text-primary" />
            </div>
            <CardTitle className="text-2xl">Project created!</CardTitle>
            <CardDescription className="text-base">
              Head to your dashboard to configure the search strategy, collect
              documents, and start analyzing.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-left text-sm text-muted-foreground">
            <div className="flex items-start gap-3">
              <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">
                1
              </span>
              <div>
                <p className="font-medium text-foreground">Configure search</p>
                <p>Open your project and click "Search Strategy" to define keywords and sources.</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">
                2
              </span>
              <div>
                <p className="font-medium text-foreground">Collect documents</p>
                <p>Click "Collect Now" to fetch documents from academic databases.</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">
                3
              </span>
              <div>
                <p className="font-medium text-foreground">Generate insights</p>
                <p>Build the knowledge graph, run AI analysis, and generate reports.</p>
              </div>
            </div>
          </CardContent>
          <CardFooter>
            <Button className="w-full gap-2" size="lg" onClick={goToProject}>
              Go to dashboard
              <ArrowRight className="h-4 w-4" />
            </Button>
          </CardFooter>
        </Card>
      )}
    </div>
  );
}
