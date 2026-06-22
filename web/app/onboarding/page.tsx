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
  name: z.string().min(1, "El nombre del proyecto es obligatorio").max(200),
  topic: z.string().min(1, "El tema de investigación es obligatorio").max(500),
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
      toast.error(err?.detail || "Error al crear el proyecto");
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
            <CardTitle className="text-3xl">Bienvenido a VigilaGraph</CardTitle>
            <CardDescription className="text-base">
              Vigilancia tecnológica con IA. Creá tu primer proyecto
              para empezar a monitorear tendencias, tecnologías y oportunidades.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 text-left text-sm text-muted-foreground">
            <div className="flex items-start gap-3">
              <Sparkles className="mt-0.5 h-5 w-5 shrink-0 text-primary" />
              <div>
                <p className="font-medium text-foreground">Definí tu tema</p>
                <p>Buscamos en bases de datos académicas y la web documentos relevantes.</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <Sparkles className="mt-0.5 h-5 w-5 shrink-0 text-primary" />
              <div>
                <p className="font-medium text-foreground">Análisis con IA</p>
                <p>Identificá tecnologías, tendencias, actores y oportunidades automáticamente.</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <Sparkles className="mt-0.5 h-5 w-5 shrink-0 text-primary" />
              <div>
                <p className="font-medium text-foreground">Grafos de conocimiento</p>
                <p>Visualizá conexiones entre conceptos con grafos interactivos.</p>
              </div>
            </div>
          </CardContent>
          <CardFooter>
            <Button className="w-full gap-2" size="lg" onClick={() => setStep("create")}>
              Creá tu primer proyecto
              <ArrowRight className="h-4 w-4" />
            </Button>
          </CardFooter>
        </Card>
      )}

      {step === "create" && (
        <Card className="w-full max-w-lg">
          <CardHeader>
            <CardTitle>Creá tu primer proyecto</CardTitle>
            <CardDescription>
              Contanos qué querés investigar — la IA se encarga del resto.
            </CardDescription>
          </CardHeader>
          <form onSubmit={handleSubmit(onSubmit)}>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Nombre del proyecto</Label>
                <Input
                  id="name"
                  placeholder="Ej: Control biológico de plagas I+D"
                  {...register("name")}
                />
                {errors.name && (
                  <p className="text-xs text-destructive">{errors.name.message}</p>
                )}
              </div>
              <div className="space-y-2">
                <Label htmlFor="topic">Tema de investigación</Label>
                <Input
                  id="topic"
                  placeholder="Ej: Control biológico usando enemigos naturales"
                  {...register("topic")}
                />
                {errors.topic && (
                  <p className="text-xs text-destructive">{errors.topic.message}</p>
                )}
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">Descripción (opcional)</Label>
                <Textarea
                  id="description"
                  placeholder="Breve descripción de tus objetivos de investigación..."
                  rows={3}
                  {...register("description")}
                />
              </div>
              <div className="space-y-2">
                <Label>Tipo de vigilancia</Label>
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
                    <SelectItem value="tecnologica">Tecnológica</SelectItem>
                    <SelectItem value="cientifica">Científica</SelectItem>
                    <SelectItem value="competitiva">Competitiva</SelectItem>
                    <SelectItem value="estrategica">Estratégica</SelectItem>
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
                Volver
              </Button>
              <Button type="submit" className="flex-1 gap-2" disabled={createProject.isPending}>
                {createProject.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Sparkles className="h-4 w-4" />
                )}
                Crear proyecto
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
            <CardTitle className="text-2xl">¡Proyecto creado!</CardTitle>
            <CardDescription className="text-base">
              Andá al panel para configurar la estrategia de búsqueda, recolectar
              documentos y empezar a analizar.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-left text-sm text-muted-foreground">
            <div className="flex items-start gap-3">
              <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">
                1
              </span>
              <div>
                <p className="font-medium text-foreground">Configurar búsqueda</p>
                <p>Abrí tu proyecto y hacé clic en "Estrategia de búsqueda" para definir palabras clave y fuentes.</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">
                2
              </span>
              <div>
                <p className="font-medium text-foreground">Recolectar documentos</p>
                <p>Hacé clic en "Recolectar" para obtener documentos de bases de datos académicas.</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">
                3
              </span>
              <div>
                <p className="font-medium text-foreground">Generar hallazgos</p>
                <p>Construí el grafo de conocimiento, ejecutá el análisis con IA y generá informes.</p>
              </div>
            </div>
          </CardContent>
          <CardFooter>
            <Button className="w-full gap-2" size="lg" onClick={goToProject}>
              Ir al panel
              <ArrowRight className="h-4 w-4" />
            </Button>
          </CardFooter>
        </Card>
      )}
    </div>
  );
}
