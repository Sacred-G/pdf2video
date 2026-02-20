"use client";

import { Images, X } from "lucide-react";

interface ImageDropzoneProps {
  files: File[];
  onFilesChange: (files: File[]) => void;
}

export function ImageDropzone({ files, onFilesChange }: ImageDropzoneProps) {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files;
    if (!selected) return;
    onFilesChange([...files, ...Array.from(selected)]);
  };

  const removeFile = (index: number) => {
    onFilesChange(files.filter((_, i) => i !== index));
  };

  return (
    <div className="space-y-2">
      <label className="surface group block cursor-pointer rounded-2xl border-dashed p-6 transition hover:border-cyan-300/50">
        <div className="flex items-center gap-3">
          <Images className="h-6 w-6 text-cyan-200/80" />
          <div>
            <p className="font-medium">Upload images</p>
            <p className="text-sm text-cyan-100/70">PNG / JPG / WEBP · multi-select enabled</p>
          </div>
        </div>
        <input className="hidden" type="file" multiple accept="image/png,image/jpeg,image/webp" onChange={handleChange} />
      </label>
      {files.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {files.map((f, i) => (
            <span key={`${f.name}-${i}`} className="inline-flex items-center gap-1 rounded-full bg-cyan-400/10 px-2 py-1 text-xs text-cyan-100/80">
              {f.name}
              <button type="button" onClick={() => removeFile(i)} className="rounded-full p-0.5 hover:bg-cyan-300/20">
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
