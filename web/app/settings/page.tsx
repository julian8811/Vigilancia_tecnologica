"use client";

import { useAuth } from "@/hooks/use-auth";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Settings, User } from "lucide-react";

export default function SettingsPage() {
  const { user } = useAuth();

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Configuración</h2>
        <p className="text-muted-foreground">
          Administrá tu cuenta.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <User className="h-5 w-5" />
            Perfil
          </CardTitle>
          <CardDescription>
            Tu información personal.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div>
            <p className="text-xs text-muted-foreground">Nombre</p>
            <p className="text-sm font-medium">{user?.name || "-"}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Correo electrónico</p>
            <p className="text-sm font-medium">{user?.email || "-"}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Rol</p>
            <p className="text-sm font-medium capitalize">
              {user?.is_superuser ? "Administrador" : "Usuario"}
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
