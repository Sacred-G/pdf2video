import { ApiError } from "@/types/api";
import { getStoredToken, isTokenExpired, refreshAccessToken } from "@/lib/auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function apiFetch<T>(path: string, init: RequestInit = {}, token?: string): Promise<T> {
  const headers = new Headers(init.headers);

  // Only set Content-Type for non-FormData bodies (FormData sets its own boundary)
  const isFormData = init.body instanceof FormData;
  if (!isFormData && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  // Auto-attach token from store if not explicitly provided
  let authToken = token ?? getStoredToken();
  if (authToken && isTokenExpired(authToken)) {
    authToken = await refreshAccessToken();
  }
  if (authToken) headers.set("Authorization", `Bearer ${authToken}`);

  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers,
    credentials: "include"
  });

  // Auto-redirect to login on 401
  if (response.status === 401 && typeof window !== "undefined") {
    const { useAuthStore } = await import("@/stores/auth-store");
    const { clearStoredToken } = await import("@/lib/auth");
    clearStoredToken();
    useAuthStore.getState().clear();
    window.location.href = "/login";
    throw { code: "UNAUTHORIZED", message: "Session expired" } as ApiError;
  }

  if (!response.ok) {
    let error: ApiError = { code: "UNKNOWN", message: "Request failed" };
    try {
      const body = await response.json();
      error = { code: body.code ?? body.detail ?? "UNKNOWN", message: body.message ?? body.detail ?? response.statusText };
    } catch {
      error.message = response.statusText;
    }
    throw error;
  }

  // Handle empty responses (204, etc.)
  const text = await response.text();
  if (!text) return {} as T;
  return JSON.parse(text) as T;
}
