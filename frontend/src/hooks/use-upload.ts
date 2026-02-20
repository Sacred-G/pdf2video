"use client";

import { useCallback, useState } from "react";
import { useAuthStore } from "@/stores/auth-store";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type UploadType = "pdf" | "images" | "music";

export interface UploadedFile {
  id: string;
  originalFilename: string;
  fileSize: number;
  mimeType: string;
  storedPath: string;
}

interface UploadState {
  uploading: boolean;
  progress: number;
  error: string | null;
}

export function useUpload() {
  const { token } = useAuthStore();
  const [state, setState] = useState<UploadState>({
    uploading: false,
    progress: 0,
    error: null,
  });

  const upload = useCallback(
    (type: UploadType, files: File[]): Promise<UploadedFile[]> => {
      return new Promise((resolve, reject) => {
        const formData = new FormData();
        files.forEach((file) => formData.append("files", file));

        const xhr = new XMLHttpRequest();

        xhr.upload.addEventListener("progress", (e) => {
          if (e.lengthComputable) {
            setState((prev) => ({ ...prev, progress: e.loaded / e.total }));
          }
        });

        xhr.addEventListener("load", () => {
          setState({ uploading: false, progress: 1, error: null });
          if (xhr.status >= 200 && xhr.status < 300) {
            resolve(JSON.parse(xhr.responseText) as UploadedFile[]);
          } else {
            const msg = `Upload failed: ${xhr.statusText}`;
            setState((prev) => ({ ...prev, error: msg }));
            reject(new Error(msg));
          }
        });

        xhr.addEventListener("error", () => {
          const msg = "Network error during upload";
          setState({ uploading: false, progress: 0, error: msg });
          reject(new Error(msg));
        });

        setState({ uploading: true, progress: 0, error: null });
        xhr.open("POST", `${API_URL}/api/v1/uploads/${type}`);
        if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
        xhr.send(formData);
      });
    },
    [token]
  );

  const reset = useCallback(() => {
    setState({ uploading: false, progress: 0, error: null });
  }, []);

  return { ...state, upload, reset };
}
