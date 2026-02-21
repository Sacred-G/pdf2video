"use client";

import { useState } from "react";
import { Pencil, Star, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { usePresets } from "@/hooks/use-presets";

export default function SettingsPage() {
  const { presets, loading, updatePreset, deletePreset } = usePresets();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");

  async function handleSetDefault(id: string) {
    try {
      await updatePreset(id, { is_default: true });
      toast.success("Default preset updated");
    } catch {
      toast.error("Failed to update default");
    }
  }

  async function handleRename(id: string) {
    if (!editName.trim()) return;
    try {
      await updatePreset(id, { name: editName.trim() });
      setEditingId(null);
      toast.success("Preset renamed");
    } catch {
      toast.error("Failed to rename");
    }
  }

  async function handleDelete(id: string) {
    try {
      await deletePreset(id);
      toast.success("Preset deleted");
    } catch {
      toast.error("Failed to delete");
    }
  }

  return (
    <div className="grid gap-5 lg:grid-cols-2">
      <section className="surface p-5">
        <p className="text-xs uppercase tracking-[0.2em] text-cyan-200/70">Profile</p>
        <h1 className="mt-2 text-2xl font-semibold">Account Settings</h1>
        <div className="mt-4 space-y-3">
          <input className="w-full rounded-xl border border-cyan-200/20 bg-cyan-950/40 p-3" defaultValue="You" />
          <input className="w-full rounded-xl border border-cyan-200/20 bg-cyan-950/40 p-3" defaultValue="you@example.com" />
        </div>
      </section>

      <section className="surface p-5">
        <p className="text-xs uppercase tracking-[0.2em] text-cyan-200/70">API Key</p>
        <h2 className="mt-2 text-xl font-semibold">OpenAI Credential</h2>
        <input
          type="password"
          placeholder="sk-..."
          className="mt-4 w-full rounded-xl border border-cyan-200/20 bg-cyan-950/40 p-3"
        />
        <button className="mt-4 rounded-lg bg-gradient-to-r from-teal-400 to-orange-300 px-4 py-2 font-semibold text-slate-950">
          Save Securely
        </button>
      </section>

      <section className="surface col-span-full p-5">
        <p className="text-xs uppercase tracking-[0.2em] text-cyan-200/70">Presets</p>
        <h2 className="mt-2 text-xl font-semibold">Saved Generation Settings</h2>
        <p className="mt-1 text-sm text-cyan-100/60">
          Manage your saved presets. The default preset auto-loads when creating a new job.
        </p>

        {loading ? (
          <p className="mt-4 text-sm text-cyan-100/50">Loading presets...</p>
        ) : presets.length === 0 ? (
          <p className="mt-4 text-sm text-cyan-100/50">
            No presets yet. Save one from the Create page.
          </p>
        ) : (
          <div className="mt-4 space-y-2">
            {presets.map((preset) => (
              <div
                key={preset.id}
                className="flex items-center justify-between gap-3 rounded-xl border border-cyan-200/10 bg-cyan-950/30 p-3"
              >
                <div className="min-w-0 flex-1">
                  {editingId === preset.id ? (
                    <input
                      value={editName}
                      onChange={(e) => setEditName(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && handleRename(preset.id)}
                      onBlur={() => setEditingId(null)}
                      className="w-full rounded-lg bg-cyan-950/60 px-2 py-1 text-sm outline-none"
                      autoFocus
                    />
                  ) : (
                    <div>
                      <span className="font-medium">{preset.name}</span>
                      {preset.is_default && (
                        <span className="ml-2 rounded-full bg-amber-500/20 px-2 py-0.5 text-xs text-amber-200">
                          Default
                        </span>
                      )}
                      <p className="mt-0.5 text-xs text-cyan-100/50">
                        {preset.settings.voice} · {preset.settings.resolution} · {preset.settings.fps}fps
                        {preset.settings.generate_backgrounds ? " · AI BG" : ""}
                      </p>
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-1">
                  {!preset.is_default && (
                    <button
                      onClick={() => handleSetDefault(preset.id)}
                      title="Set as default"
                      className="rounded-lg p-1.5 text-cyan-100/40 hover:bg-cyan-400/10 hover:text-amber-300"
                    >
                      <Star className="h-4 w-4" />
                    </button>
                  )}
                  <button
                    onClick={() => { setEditingId(preset.id); setEditName(preset.name); }}
                    title="Rename"
                    className="rounded-lg p-1.5 text-cyan-100/40 hover:bg-cyan-400/10 hover:text-cyan-100"
                  >
                    <Pencil className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => handleDelete(preset.id)}
                    title="Delete"
                    className="rounded-lg p-1.5 text-cyan-100/40 hover:bg-rose-400/10 hover:text-rose-300"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
