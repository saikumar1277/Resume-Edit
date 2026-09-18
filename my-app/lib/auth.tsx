"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { apiFetch, ApiError } from "@/lib/api";

export type AuthUser = {
  id: string;
  email: string;
};

type AuthContextValue = {
  user: AuthUser | null;
  loading: boolean;
  refresh: () => Promise<void>;
  login: (email: string, password: string) => Promise<AuthUser>;
  signup: (email: string, password: string) => Promise<AuthUser>;
  logout: () => Promise<void>;
  resendVerify: (email: string) => Promise<void>;
  forgotPassword: (email: string) => Promise<void>;
  verifyEmail: (token: string) => Promise<AuthUser>;
  resetPassword: (token: string, password: string) => Promise<AuthUser>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

function detailMessage(payload: unknown, fallback: string): string {
  if (!payload || typeof payload !== "object") return fallback;
  const detail = (payload as { detail?: unknown }).detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail[0] && typeof detail[0] === "object") {
    const first = detail[0] as { msg?: string };
    if (first.msg) return String(first.msg);
  }
  return fallback;
}

function detailCode(payload: unknown): string | undefined {
  if (!payload || typeof payload !== "object") return undefined;
  const detail = (payload as { detail?: unknown }).detail;
  return typeof detail === "string" ? detail : undefined;
}

async function readJson<T>(path: string, body?: unknown): Promise<T> {
  const res = await apiFetch(path, {
    method: body ? "POST" : "GET",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  const payload = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new ApiError(
      detailMessage(payload, "Request failed."),
      res.status,
      detailCode(payload),
    );
  }
  return payload as T;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const next = await readJson<AuthUser>("/auth/me");
      setUser(next);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const login = useCallback(async (email: string, password: string) => {
    const next = await readJson<AuthUser>("/auth/login", { email, password });
    setUser(next);
    return next;
  }, []);

  const signup = useCallback(async (email: string, password: string) => {
    const next = await readJson<AuthUser>("/auth/signup", { email, password });
    setUser(next);
    return next;
  }, []);

  const logout = useCallback(async () => {
    await apiFetch("/auth/logout", { method: "POST" });
    setUser(null);
  }, []);

  const resendVerify = useCallback(async (email: string) => {
    await readJson("/auth/resend-verify", { email });
  }, []);

  const forgotPassword = useCallback(async (email: string) => {
    await readJson("/auth/forgot", { email });
  }, []);

  const verifyEmail = useCallback(async (token: string) => {
    const next = await readJson<AuthUser>("/auth/verify", { token });
    setUser(next);
    return next;
  }, []);

  const resetPassword = useCallback(async (token: string, password: string) => {
    const next = await readJson<AuthUser>("/auth/reset", { token, password });
    setUser(next);
    return next;
  }, []);

  const value = useMemo(
    () => ({
      user,
      loading,
      refresh,
      login,
      signup,
      logout,
      resendVerify,
      forgotPassword,
      verifyEmail,
      resetPassword,
    }),
    [
      user,
      loading,
      refresh,
      login,
      signup,
      logout,
      resendVerify,
      forgotPassword,
      verifyEmail,
      resetPassword,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return value;
}

export function safeNextPath(raw: string | null | undefined): string {
  if (raw && raw.startsWith("/") && !raw.startsWith("//")) return raw;
  return "/resumes";
}
