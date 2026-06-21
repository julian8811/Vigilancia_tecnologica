"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { useCreateProject } from "@/hooks/use-projects";
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
import { Loader2, ArrowLeft } from "lucide-react";
import Link from "next/link";
import type { SurveillanceType } from "@/types/api";

const createProjectSchema = z.object({
  name: z.string().min(1, "Name is required").max(200),
  topic: z.string().min(1, "Topic is required").max(500),
  description: z.string().optional(),
  surveillance_type: z.string().min(1, "Surveillance type is required"),
  language: z.string().min(1, "Language is required"),
  slug: z.string().optional(),
});

type CreateProjectForm = z.infer<typeof createProjectSchema>;

const surveillanceTypes: { value: SurveillanceType; label: string }[] = [
  { value: "tecnologica", label: "Technological" },
  { value: "cientifica", label: "Scientific" },
  { value: "competitiva", label: "Competitive" },
  { value: "estrategica", label: "Strategic" },
  { value: "patentaria", label: "Patent" },
  { value: "mercado", label: "Market" },
  { value: "academica", label: "Academic" },
];

const languages = [
  { value: "es", label: "Spanish" },
  { value: "en", label: "English" },
  { value: "pt", label: "Portuguese" },
  { value: "fr", label: "French" },
  { value: "de", label: "German" },
  { value: "zh", label: "Chinese" },
  { value: "ja", label: "Japanese" },
];

export default function CreateProjectPage() {
  const router = useRouter();
  const createProject = useCreateProject();
  const [submitting, setSubmitting] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
    watch,
  } = useForm<CreateProjectForm>({
    resolver: zodResolver(createProjectSchema),
    defaultValues: {
      surveillance_type: "full",
      language: "es",
    },
  });

  const watchType = watch("surveillance_type");
  const watchLang = watch("language");

  const onSubmit = async (data: CreateProjectForm) => {
    setSubmitting(true);
    try {
      const project = await createProject.mutateAsync({
        name: data.name,
        topic: data.topic,
        description: data.description || undefined,
        surveillance_type: data.surveillance_type as SurveillanceType,
        language: data.language,
        slug: data.slug || undefined,
      });
      toast.success("Project created!");
      router.push(`/projects/${project.id}`);
    } catch (err: any) {
      toast.error(err?.detail || err?.message || "Failed to create project");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" asChild>
          <Link href="/projects">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <div>
          <h2 className="text-2xl font-bold tracking-tight">
            Create Project
          </h2>
          <p className="text-muted-foreground">
            Define a new technology surveillance project.
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit(onSubmit)}>
        <Card>
          <CardHeader>
            <CardTitle>Project Details</CardTitle>
            <CardDescription>
              Configure the basic information for your surveillance project.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Name *</Label>
              <Input
                id="name"
                placeholder="e.g., Quantum Computing Patents"
                {...register("name")}
              />
              {errors.name && (
                <p className="text-xs text-destructive">
                  {errors.name.message}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="topic">Topic *</Label>
              <Input
                id="topic"
                placeholder="e.g., Quantum computing, AI in healthcare"
                {...register("topic")}
              />
              {errors.topic && (
                <p className="text-xs text-destructive">
                  {errors.topic.message}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                placeholder="Optional project description..."
                rows={3}
                {...register("description")}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="slug">Slug (optional)</Label>
              <Input
                id="slug"
                placeholder="Auto-generated from name if empty"
                {...register("slug")}
              />
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label>Surveillance Type *</Label>
                <Select
                  value={watchType}
                  onValueChange={(v) =>
                    setValue("surveillance_type", v, { shouldValidate: true })
                  }
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select type" />
                  </SelectTrigger>
                  <SelectContent>
                    {surveillanceTypes.map((t) => (
                      <SelectItem key={t.value} value={t.value}>
                        {t.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {errors.surveillance_type && (
                  <p className="text-xs text-destructive">
                    {errors.surveillance_type.message}
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <Label>Language *</Label>
                <Select
                  value={watchLang}
                  onValueChange={(v) =>
                    setValue("language", v, { shouldValidate: true })
                  }
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select language" />
                  </SelectTrigger>
                  <SelectContent>
                    {languages.map((l) => (
                      <SelectItem key={l.value} value={l.value}>
                        {l.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {errors.language && (
                  <p className="text-xs text-destructive">
                    {errors.language.message}
                  </p>
                )}
              </div>
            </div>
          </CardContent>
          <CardFooter className="flex justify-between">
            <Button variant="outline" asChild>
              <Link href="/projects">Cancel</Link>
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitting && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              Create Project
            </Button>
          </CardFooter>
        </Card>
      </form>
    </div>
  );
}
