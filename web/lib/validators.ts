import { z } from "zod";

/**
 * Shared Zod validation schemas.
 *
 * These will grow as forms are implemented throughout the app.
 */

export const emailSchema = z
  .string()
  .email("Ingresá un correo válido")
  .min(1, "El correo es obligatorio");

export const passwordSchema = z
  .string()
  .min(8, "La contraseña debe tener al menos 8 caracteres")
  .max(128, "La contraseña debe tener como máximo 128 caracteres");

export const loginSchema = z.object({
  email: emailSchema,
  password: z.string().min(1, "La contraseña es obligatoria"),
});

export type LoginInput = z.infer<typeof loginSchema>;

export const signupSchema = z
  .object({
    name: z.string().min(1, "El nombre es obligatorio").max(100),
    email: emailSchema,
    password: passwordSchema,
    confirmPassword: z.string(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Las contraseñas no coinciden",
    path: ["confirmPassword"],
  });

export type SignupInput = z.infer<typeof signupSchema>;
