"use client";

import { useCallback, useState } from "react";
import { apiFetch } from "@/lib/api-client";

export function useApi<T>() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const request = useCallback(async (path: string, init?: RequestInit, token?: string) => {
    setLoading(true);
    setError(null);
    try {
      return await apiFetch<T>(path, init, token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return { loading, error, request };
}
