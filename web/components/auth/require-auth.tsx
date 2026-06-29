"use client";

import { useEffect, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";
import { Loader2 } from "lucide-react";

/**
 * Client-side auth gate for protected pages.
 *
 * Wrap a page's content in <RequireAuth>...</RequireAuth> to:
 *   1. Show a loading spinner while auth state is resolving.
 *   2. Redirect to /login if the user is not authenticated.
 *   3. Render children otherwise.
 *
 * Note: this is a client-side check. Because auth state lives in
 * localStorage today, a fully SSR-safe middleware is not possible
 * without moving the token to an httpOnly cookie (tracked as S2 in
 * the audit). When S2 lands, replace this with a proper Next.js
 * middleware that reads the cookie.
 */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/login");
    }
  }, [loading, user, router]);

  if (loading || !user) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return <>{children}</>;
}
