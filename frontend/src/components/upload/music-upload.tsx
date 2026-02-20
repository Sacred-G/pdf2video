"use client";

import { Music, X } from "lucide-react";

interface MusicUploadProps {
  file: File | null;
  onFileChange: (file: File | null) => void;
}

export function MusicUpload({ file, onFileChange }: MusicUploadProps) {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0] ?? null;
    onFileChange(f);
  };

  return (
    <label className="surface block cursor-pointer rounded-2xl border-dashed p-4 transition hover:border-cyan-300/50">
      <div className="flex items-center gap-3">
        <Music className="h-5 w-5 text-cyan-200/80" />
        <div>
          <p className="font-medium">Background music (optional)</p>
          {file ? (
            <span className="inline-flex items-center gap-1 text-sm text-cyan-100/80">
              {file.name}
              <button
                type="button"
                onClick={(e) => { e.preventDefault(); onFileChange(null); }}
                className="rounded-full p-0.5 hover:bg-cyan-300/20"
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          ) : (
            <p className="text-sm text-cyan-100/70">MP3, WAV, OGG, M4A</p>
          )}
        </div>
      </div>
      <input className="hidden" type="file" accept="audio/mpeg,audio/wav,audio/ogg,audio/mp4" onChange={handleChange} />
    </label>
  );
}
