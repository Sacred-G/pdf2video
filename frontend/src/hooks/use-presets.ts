"use client";

import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "@/lib/api-client";
import { Preset, PresetListResponse, PresetSettings } from "@/types/preset";

export function usePresets() {
  const [presets, setPresets] = useState<Preset[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchPresets = useCallback(async () => {
    try {
      setLoading(true);
      const data = await apiFetch<PresetListResponse>("/api/v1/presets");
      setPresets(data.items);
    } catch {
      // Silently fail — presets are optional
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPresets();
  }, [fetchPresets]);

  const createPreset = useCallback(
    async (name: string, description: string, settings: PresetSettings, isDefault = false) => {
      const preset = await apiFetch<Preset>("/api/v1/presets", {
        method: "POST",
        body: JSON.stringify({
          name,
          description,
          settings,
          is_default: isDefault,
        }),
      });
      setPresets((prev) => [preset, ...prev]);
      return preset;
    },
    []
  );

  const updatePreset = useCallback(
    async (id: string, data: Partial<{ name: string; description: string; settings: PresetSettings; is_default: boolean }>) => {
      const updated = await apiFetch<Preset>(`/api/v1/presets/${id}`, {
        method: "PUT",
        body: JSON.stringify(data),
      });
      setPresets((prev) => prev.map((p) => (p.id === id ? updated : p)));
      return updated;
    },
    []
  );

  const deletePreset = useCallback(async (id: string) => {
    await apiFetch(`/api/v1/presets/${id}`, { method: "DELETE" });
    setPresets((prev) => prev.filter((p) => p.id !== id));
  }, []);

  const defaultPreset = presets.find((p) => p.is_default) ?? null;

  return { presets, loading, defaultPreset, fetchPresets, createPreset, updatePreset, deletePreset };
}
