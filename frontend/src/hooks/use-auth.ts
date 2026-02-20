"use client";

import { useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/auth-store";
import { apiFetch } from "@/lib/api-client";
import { storeToken, clearStoredToken } from "@/lib/auth";

interface LoginPayload {
  email: string;
  password: string;
}

interface RegisterPayload {
  email: string;
  password: string;
  displayName: string;
}

interface TokenResponse {
  access_token: string;
  token_type: string;
}

export function useAuth() {
  const { token, email, setAuth, clear } = useAuthStore();
  const router = useRouter();

  const login = useCallback(
    async (payload: LoginPayload) => {
      const data = await apiFetch<TokenResponse>("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      storeToken(data.access_token);
      setAuth({ token: data.access_token, email: payload.email });
      router.push("/");
    },
    [setAuth, router]
  );

  const register = useCallback(
    async (payload: RegisterPayload) => {
      const data = await apiFetch<TokenResponse>("/api/v1/auth/register", {
        method: "POST",
        body: JSON.stringify({
          email: payload.email,
          password: payload.password,
          display_name: payload.displayName,
        }),
      });
      storeToken(data.access_token);
      setAuth({ token: data.access_token, email: payload.email });
      router.push("/");
    },
    [setAuth, router]
  );

  const logout = useCallback(async () => {
    try {
      await apiFetch("/api/v1/auth/logout", { method: "POST" }, token ?? undefined);
    } catch {
      // best-effort
    }
    clearStoredToken();
    clear();
    router.push("/login");
  }, [token, clear, router]);

  return {
    token,
    email,
    isAuthenticated: !!token,
    login,
    register,
    logout,
  };
}
