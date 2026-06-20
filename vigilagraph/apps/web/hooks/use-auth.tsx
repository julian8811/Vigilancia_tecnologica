"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";
import { api, setAuthToken } from "@/lib/api";
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
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    const t = localStorage.getItem("token");
    if (t) {
      setToken(t);
      setAuthToken(t);
      api
        .get<User>("/auth/me")
        .then((u) => setUser(u))
        .catch(() => {
          localStorage.removeItem("token");
          setAuthToken(null);
          setToken(null);
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const formData = new URLSearchParams();
    formData.append("username", email);
    formData.append("password", password);

    const data = await api.post<{ access_token: string; token_type: string }>(
      "/auth/login",
      formData.toString(),
      { headers: { "Content-Type": "application/x-www-form-urlencoded" } },
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
    localStorage.removeItem("token");
    setAuthToken(null);
    setToken(null);
    setUser(null);
  }, []);

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
