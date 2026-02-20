"use client";

import { FileText, UploadCloud, X } from "lucide-react";

interface PdfDropzoneProps {
  file: File | null;
  onFileChange: (file: File | null) => void;
}

export function PdfDropzone({ file, onFileChange }: PdfDropzoneProps) {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0] ?? null;
    onFileChange(f);
  };

  return (
    <label className="surface group flex cursor-pointer flex-col items-center justify-center rounded-2xl border-dashed p-8 text-center transition hover:border-cyan-300/50">
      <UploadCloud className="h-8 w-8 text-cyan-200/80 transition group-hover:scale-110" />
      {file ? (
        <div className="mt-3 flex items-center gap-2">
          <FileText className="h-4 w-4 text-cyan-300" />
          <span className="text-sm font-medium">{file.name}</span>
          <button
            type="button"
            onClick={(e) => { e.preventDefault(); onFileChange(null); }}
            className="rounded-full p-0.5 hover:bg-cyan-300/20"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      ) : (
        <>
          <p className="mt-3 text-lg font-medium">Drop PDF here</p>
          <p className="mt-1 text-sm text-cyan-100/70">or click to browse files</p>
        </>
      )}
      <input type="file" accept="application/pdf" className="hidden" onChange={handleChange} />
      <div className="mt-4 inline-flex items-center gap-2 rounded-full bg-cyan-400/10 px-3 py-1 text-xs text-cyan-100/80">
        <FileText className="h-3.5 w-3.5" />
        Up to 100MB
      </div>
    </label>
  );
}
