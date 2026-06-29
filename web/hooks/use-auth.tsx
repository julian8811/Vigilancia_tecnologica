"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { api, setOnUnauthorized } from "@/lib/api";
import type { User } from "@/types/api";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: {
    email: string;
    password: string;
    name: string;
    organization_name?: string;
  }) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const clearSession = useCallback(
    (reason: "manual" | "expired" = "manual") => {
      setUser(null);
      if (reason === "expired") {
        toast.error("Tu sesión expiró. Volvé a iniciar sesión.");
        router.replace("/login");
      }
    },
    [router],
  );

  // Register the 401 interceptor. Runs once on mount; cleared when
  // the user logs out or the component unmounts.
  useEffect(() => {
    setOnUnauthorized(() => clearSession("expired"));
    return () => setOnUnauthorized(null);
  }, [clearSession]);

  // Bootstrap: try /auth/me. The browser sends the vg_access cookie
  // automatically. If the access token is expired, /auth/me returns
  // 401, our interceptor does nothing yet (because we have no
  // user), and we attempt /auth/refresh once.
  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      try {
        const me = await api.get<User>("/auth/me");
        if (!cancelled) setUser(me);
      } catch {
        // Try refresh.
        try {
          const refreshed = await api.post<{ user: User }>("/auth/refresh");
          if (!cancelled) setUser(refreshed.user);
        } catch {
          // Both failed; user is anonymous.
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const data = await api.post<{ user: User }>("/auth/login", { email, password });
    setUser(data.user);
  }, []);

  const register = useCallback(
    async (data: {
      email: string;
      password: string;
      name: string;
      organization_name?: string;
    }) => {
      await api.post("/auth/register", data);
    },
    [],
  );

  const logout = useCallback(async () => {
    try {
      await api.post("/auth/logout");
    } catch {
      // Logout is best-effort; the server clears the cookie via
      // Set-Cookie Max-Age=0, the local state is cleared below.
    }
    clearSession("manual");
  }, [clearSession]);

  const refresh = useCallback(async () => {
    const data = await api.post<{ user: User }>("/auth/refresh");
    setUser(data.user);
  }, []);

  return (
    <AuthContext.Provider
      value={{ user, loading, login, register, logout, refresh }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
