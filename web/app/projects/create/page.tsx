"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { useCreateProject } from "@/hooks/use-projects";
import { RequireAuth } from "@/components/auth/require-auth";
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
  name: z.string().min(1, "El nombre es obligatorio").max(200),
  topic: z.string().min(1, "El tema es obligatorio").max(500),
  description: z.string().optional(),
  surveillance_type: z.string().min(1, "El tipo de vigilancia es obligatorio"),
  language: z.string().min(1, "El idioma es obligatorio"),
  slug: z.string().optional(),
});

type CreateProjectForm = z.infer<typeof createProjectSchema>;

const surveillanceTypes: { value: SurveillanceType; label: string }[] = [
  { value: "tecnologica", label: "Tecnológica" },
  { value: "cientifica", label: "Científica" },
  { value: "competitiva", label: "Competitiva" },
  { value: "estrategica", label: "Estratégica" },
  { value: "patentaria", label: "Patentaria" },
  { value: "mercado", label: "Mercado" },
  { value: "academica", label: "Académica" },
];

const languages = [
  { value: "es", label: "Español" },
  { value: "en", label: "Inglés" },
  { value: "pt", label: "Portugués" },
  { value: "fr", label: "Francés" },
  { value: "de", label: "Alemán" },
  { value: "zh", label: "Chino" },
  { value: "ja", label: "Japonés" },
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
      toast.success("¡Proyecto creado!");
      router.push(`/projects/${project.id}`);
    } catch (err: any) {
      toast.error(err?.detail || err?.message || "Error al crear proyecto");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <RequireAuth>
    <div className="mx-auto max-w-2xl space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" asChild>
          <Link href="/projects">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <div>
          <h2 className="text-2xl font-bold tracking-tight">
            Crear proyecto
          </h2>
          <p className="text-muted-foreground">
            Definí un nuevo proyecto de vigilancia tecnológica.
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit(onSubmit)}>
        <Card>
          <CardHeader>
            <CardTitle>Detalles del proyecto</CardTitle>
            <CardDescription>
              Configurá la información básica de tu proyecto.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Nombre *</Label>
              <Input
                id="name"
                placeholder="Ej: Patentes de computación cuántica"
                {...register("name")}
              />
              {errors.name && (
                <p className="text-xs text-destructive">
                  {errors.name.message}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="topic">Tema *</Label>
              <Input
                id="topic"
                placeholder="Ej: Computación cuántica, IA en salud"
                {...register("topic")}
              />
              {errors.topic && (
                <p className="text-xs text-destructive">
                  {errors.topic.message}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">Descripción</Label>
              <Textarea
                id="description"
                placeholder="Descripción opcional del proyecto..."
                rows={3}
                {...register("description")}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="slug">Slug (opcional)</Label>
              <Input
                id="slug"
                placeholder="Se genera automáticamente si está vacío"
                {...register("slug")}
              />
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label>Tipo de vigilancia *</Label>
                <Select
                  value={watchType}
                  onValueChange={(v) =>
                    setValue("surveillance_type", v, { shouldValidate: true })
                  }
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Seleccionar tipo" />
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
                <Label>Idioma *</Label>
                <Select
                  value={watchLang}
                  onValueChange={(v) =>
                    setValue("language", v, { shouldValidate: true })
                  }
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Seleccionar idioma" />
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
    </RequireAuth>
    );
  }
