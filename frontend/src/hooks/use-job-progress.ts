"use client";

import { useEffect, useMemo, useState } from "react";
import { JobProgress } from "@/types/job";

const FALLBACK_STEPS = [
  { status: "classifying", step: "Classifying images", progress: 0.2 },
  { status: "scripting", step: "Generating script", progress: 0.4 },
  { status: "voiceover", step: "Generating voiceover", progress: 0.6 },
  { status: "composing", step: "Composing video", progress: 0.8 },
  { status: "completed", step: "Complete", progress: 1 }
] as const;

export function useJobProgress(jobId: string) {
  const [progress, setProgress] = useState<JobProgress>({
    status: "pending",
    step: "Queued",
    progress: 0
  });
  const [sseConnected, setSseConnected] = useState(false);

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    if (!apiUrl) return;

    const stream = new EventSource(`${apiUrl}/api/v1/jobs/${jobId}/progress`, {
      withCredentials: true
    });

    stream.addEventListener("progress", (event) => {
      setSseConnected(true);
      const payload = JSON.parse((event as MessageEvent).data) as JobProgress;
      setProgress(payload);
    });

    stream.onerror = () => {
      stream.close();
    };

    return () => stream.close();
  }, [jobId]);

  useEffect(() => {
    if (progress.status !== "pending" || sseConnected) return;

    let i = 0;
    const timer = setInterval(() => {
      const next = FALLBACK_STEPS[Math.min(i, FALLBACK_STEPS.length - 1)];
      setProgress({
        status: next.status,
        step: next.step,
        progress: next.progress
      });
      i += 1;
      if (i >= FALLBACK_STEPS.length) clearInterval(timer);
    }, 1500);

    return () => clearInterval(timer);
  }, [progress.status, sseConnected]);

  return useMemo(() => progress, [progress]);
}
