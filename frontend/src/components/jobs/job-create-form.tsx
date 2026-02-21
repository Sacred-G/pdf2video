"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { ArrowRight, Loader2, Save, FolderOpen } from "lucide-react";
import { toast } from "sonner";

import { fpsOptions, resolutions, voices } from "@/lib/constants";
import { PdfDropzone } from "@/components/upload/pdf-dropzone";
import { ImageDropzone } from "@/components/upload/image-dropzone";
import { MusicUpload } from "@/components/upload/music-upload";
import { useUpload } from "@/hooks/use-upload";
import { usePresets } from "@/hooks/use-presets";
import { apiFetch } from "@/lib/api-client";
import { Preset } from "@/types/preset";

interface JobResponse {
  id: string;
}

interface UploadedFile {
  id: string;
}

const steps = ["Input", "Configure", "Review"] as const;

export function JobCreateForm() {
  const router = useRouter();
  const { upload } = useUpload();
  const { presets, defaultPreset, createPreset } = usePresets();
  const [step, setStep] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [savingPreset, setSavingPreset] = useState(false);
  const [presetName, setPresetName] = useState("");
  const [showSavePreset, setShowSavePreset] = useState(false);

  // Step 0 — Input
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [imageFiles, setImageFiles] = useState<File[]>([]);
  const [textContent, setTextContent] = useState("");
  const [title, setTitle] = useState("");

  // Step 1 — Configure
  const [voice, setVoice] = useState(voices[0]);
  const [resolution, setResolution] = useState(resolutions[0]);
  const [fps, setFps] = useState(fpsOptions[1]); // 30
  const [generateBackgrounds, setGenerateBackgrounds] = useState(true);
  const [musicFile, setMusicFile] = useState<File | null>(null);

  // Auto-load default preset on mount
  useEffect(() => {
    if (defaultPreset) {
      applyPreset(defaultPreset);
    }
  }, [defaultPreset]);

  function applyPreset(preset: Preset) {
    const s = preset.settings;
    if (s.voice && voices.includes(s.voice)) setVoice(s.voice);
    if (s.resolution && resolutions.includes(s.resolution)) setResolution(s.resolution);
    if (s.fps && fpsOptions.includes(s.fps)) setFps(s.fps);
    if (typeof s.generate_backgrounds === "boolean") setGenerateBackgrounds(s.generate_backgrounds);
    toast.success(`Loaded preset: ${preset.name}`);
  }

  async function handleSavePreset() {
    if (!presetName.trim()) {
      toast.error("Enter a preset name");
      return;
    }
    setSavingPreset(true);
    try {
      await createPreset(presetName.trim(), "", {
        voice,
        resolution,
        fps,
        generate_backgrounds: generateBackgrounds,
      });
      toast.success(`Preset "${presetName}" saved`);
      setShowSavePreset(false);
      setPresetName("");
    } catch {
      toast.error("Failed to save preset");
    } finally {
      setSavingPreset(false);
    }
  }

  const sourceType = pdfFile ? "pdf" : "text_images";
  const hasInput = pdfFile || imageFiles.length > 0 || textContent.trim().length > 0;

  const handleSubmit = async () => {
    if (!hasInput) {
      toast.error("Please provide a PDF, images, or text content");
      return;
    }

    setSubmitting(true);
    try {
      // 1. Upload files
      let pdfUploadId: string | null = null;
      let imageUploadIds: string[] = [];
      let musicUploadId: string | null = null;

      if (pdfFile) {
        const result = await upload("pdf", [pdfFile]);
        pdfUploadId = result[0]?.id ?? null;
      }

      if (imageFiles.length > 0) {
        const result = await upload("images", imageFiles);
        imageUploadIds = result.map((r: UploadedFile) => r.id);
      }

      if (musicFile) {
        const result = await upload("music", [musicFile]);
        musicUploadId = result[0]?.id ?? null;
      }

      // 2. Create job
      const job = await apiFetch<JobResponse>("/api/v1/jobs", {
        method: "POST",
        body: JSON.stringify({
          source_type: sourceType,
          title: title || (pdfFile?.name?.replace(".pdf", "") ?? "Untitled"),
          pdf_upload_id: pdfUploadId,
          image_upload_ids: imageUploadIds,
          music_upload_id: musicUploadId,
          text_content: textContent || null,
          settings: {
            voice,
            resolution,
            fps,
            generate_backgrounds: generateBackgrounds,
          },
        }),
      });

      toast.success("Job created! Redirecting to progress...");
      router.push(`/jobs/${job.id}`);
    } catch (err: any) {
      toast.error(err?.message ?? "Failed to create job");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-2">
        {steps.map((label, i) => (
          <span
            key={label}
            className={`rounded-full px-3 py-1 text-xs ${i <= step ? "bg-cyan-300/20 text-cyan-50" : "bg-slate-800 text-cyan-100/60"}`}
          >
            {i + 1}. {label}
          </span>
        ))}
      </div>

      <motion.section key={step} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
        {step === 0 ? (
          <>
            <input
              placeholder="Video title (optional)"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="surface w-full rounded-2xl p-4 outline-none"
            />
            <div className="grid gap-4 lg:grid-cols-2">
              <PdfDropzone file={pdfFile} onFileChange={setPdfFile} />
              <ImageDropzone files={imageFiles} onFilesChange={setImageFiles} />
            </div>
            <textarea
              placeholder="Or paste text content for text+images workflow..."
              value={textContent}
              onChange={(e) => setTextContent(e.target.value)}
              className="surface min-h-40 w-full resize-y rounded-2xl p-4 outline-none"
            />
          </>
        ) : null}

        {step === 1 ? (
          <div className="space-y-4">
            {/* Preset selector */}
            {presets.length > 0 && (
              <div className="flex items-center gap-2">
                <FolderOpen className="h-4 w-4 text-cyan-300" />
                <select
                  defaultValue=""
                  onChange={(e) => {
                    const preset = presets.find((p) => p.id === e.target.value);
                    if (preset) applyPreset(preset);
                  }}
                  className="surface flex-1 rounded-xl p-3 text-sm"
                >
                  <option value="" disabled>Load a saved preset...</option>
                  {presets.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}{p.is_default ? " (default)" : ""}
                    </option>
                  ))}
                </select>
              </div>
            )}

            <div className="grid gap-4 md:grid-cols-2">
              <select value={voice} onChange={(e) => setVoice(e.target.value)} className="surface rounded-xl p-3">
                {voices.map((v) => <option key={v} value={v}>{v}</option>)}
              </select>
              <select value={resolution} onChange={(e) => setResolution(e.target.value)} className="surface rounded-xl p-3">
                {resolutions.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
              <select value={String(fps)} onChange={(e) => setFps(Number(e.target.value))} className="surface rounded-xl p-3">
                {fpsOptions.map((f) => <option key={f} value={f}>{f} fps</option>)}
              </select>
              <label className="surface flex items-center gap-2 rounded-xl p-3 text-sm">
                <input type="checkbox" checked={generateBackgrounds} onChange={(e) => setGenerateBackgrounds(e.target.checked)} />
                Generate AI backgrounds
              </label>
              <div className="md:col-span-2">
                <MusicUpload file={musicFile} onFileChange={setMusicFile} />
              </div>
            </div>

            {/* Save as preset */}
            {showSavePreset ? (
              <div className="flex items-center gap-2">
                <input
                  placeholder="Preset name"
                  value={presetName}
                  onChange={(e) => setPresetName(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSavePreset()}
                  className="surface flex-1 rounded-xl p-3 text-sm outline-none"
                  autoFocus
                />
                <button
                  onClick={handleSavePreset}
                  disabled={savingPreset}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-cyan-300/20 px-3 py-2 text-sm text-cyan-50"
                >
                  {savingPreset ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}
                  Save
                </button>
                <button onClick={() => setShowSavePreset(false)} className="text-xs text-cyan-100/50 hover:text-cyan-100">
                  Cancel
                </button>
              </div>
            ) : (
              <button
                onClick={() => setShowSavePreset(true)}
                className="inline-flex items-center gap-1.5 text-sm text-cyan-100/60 hover:text-cyan-50"
              >
                <Save className="h-3.5 w-3.5" />
                Save current settings as preset
              </button>
            )}
          </div>
        ) : null}

        {step === 2 ? (
          <div className="surface space-y-3 rounded-2xl p-5">
            <h3 className="text-xl font-semibold">Review & Submit</h3>
            <div className="space-y-1 text-sm text-cyan-100/70">
              <p><strong className="text-cyan-50">Source:</strong> {sourceType === "pdf" ? `PDF — ${pdfFile?.name}` : `Text + ${imageFiles.length} images`}</p>
              <p><strong className="text-cyan-50">Voice:</strong> {voice} · <strong className="text-cyan-50">Resolution:</strong> {resolution} · <strong className="text-cyan-50">FPS:</strong> {fps}</p>
              <p><strong className="text-cyan-50">AI Backgrounds:</strong> {generateBackgrounds ? "Yes" : "No"}{musicFile ? ` · Music: ${musicFile.name}` : ""}</p>
              <p>Estimated render time: 5-8 minutes · GPU accelerated</p>
            </div>
            <button
              onClick={handleSubmit}
              disabled={submitting}
              className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-teal-300 to-orange-300 px-4 py-2 font-semibold text-slate-950 disabled:opacity-50"
            >
              {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
              {submitting ? "Uploading & Creating..." : "Generate Video"}
            </button>
          </div>
        ) : null}
      </motion.section>

      <div className="flex justify-end gap-3">
        {step > 0 && (
          <button
            onClick={() => setStep((s) => Math.max(0, s - 1))}
            className="rounded-lg border border-cyan-200/30 px-4 py-2 text-cyan-100"
          >
            Back
          </button>
        )}
        {step < steps.length - 1 && (
          <button
            onClick={() => setStep((s) => Math.min(steps.length - 1, s + 1))}
            className="inline-flex items-center gap-2 rounded-lg bg-cyan-300/20 px-4 py-2 text-cyan-50"
          >
            Continue
            <ArrowRight className="h-4 w-4" />
          </button>
        )}
      </div>
    </div>
  );
}
