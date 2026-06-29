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
import { api, setAuthToken, setOnUnauthorized } from "@/lib/api";
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
  logout: () => void;
  token: string | null;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState<string | null>(null);

  const clearSession = useCallback(
    (reason: "manual" | "expired" = "manual") => {
      localStorage.removeItem("token");
      setAuthToken(null);
      setOnUnauthorized(null);
      setToken(null);
      setUser(null);
      if (reason === "expired") {
        toast.error("Tu sesión expiró. Volvé a iniciar sesión.");
        router.replace("/login");
      }
    },
    [router],
  );

  // Register the 401 interceptor. Runs once on mount; cleared when
  // the session is cleared or the component unmounts.
  useEffect(() => {
    setOnUnauthorized(() => clearSession("expired"));
    return () => setOnUnauthorized(null);
  }, [clearSession]);

  // Bootstrap: read token from localStorage and validate it.
  useEffect(() => {
    const t = localStorage.getItem("token");
    if (t) {
      setToken(t);
      setAuthToken(t);
      api
        .get<User>("/auth/me")
        .then((u) => setUser(u))
        .catch(() => clearSession("expired"))
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, [clearSession]);

  const login = useCallback(async (email: string, password: string) => {
    const data = await api.post<{ access_token: string; token_type: string }>(
      "/auth/login",
      { email, password },
    );

    localStorage.setItem("token", data.access_token);
    setAuthToken(data.access_token);
    setToken(data.access_token);

    const me = await api.get<User>("/auth/me");
    setUser(me);
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

  const logout = useCallback(() => {
    clearSession("manual");
  }, [clearSession]);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, token }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
