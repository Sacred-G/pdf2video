"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Download, RefreshCw, XCircle } from "lucide-react";
import { toast } from "sonner";

import { JobProgress } from "@/components/jobs/job-progress";
import { SectionHeading } from "@/components/shared/section-heading";
import { useJobProgress } from "@/hooks/use-job-progress";
import { apiFetch } from "@/lib/api-client";
import { Job } from "@/types/job";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function JobDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const progress = useJobProgress(params.id);
  const [job, setJob] = useState<Job | null>(null);
  const [retrying, setRetrying] = useState(false);

  useEffect(() => {
    apiFetch<Job>(`/api/v1/jobs/${params.id}`)
      .then(setJob)
      .catch(() => {});
  }, [params.id]);

  // Re-fetch job when progress reaches terminal state
  useEffect(() => {
    if (progress.status === "completed" || progress.status === "failed") {
      apiFetch<Job>(`/api/v1/jobs/${params.id}`)
        .then(setJob)
        .catch(() => {});
    }
  }, [progress.status, params.id]);

  async function handleRetry() {
    setRetrying(true);
    try {
      const newJob = await apiFetch<Job>(`/api/v1/jobs/${params.id}/retry`, { method: "POST" });
      toast.success("Job retried! Redirecting...");
      router.push(`/jobs/${newJob.id}`);
    } catch (err: any) {
      toast.error(err?.message ?? "Failed to retry job");
    } finally {
      setRetrying(false);
    }
  }

  async function handleCancel() {
    try {
      await apiFetch(`/api/v1/jobs/${params.id}/cancel`, { method: "POST" });
      toast.success("Job cancelled");
    } catch (err: any) {
      toast.error(err?.message ?? "Failed to cancel");
    }
  }

  const isTerminal = progress.status === "completed" || progress.status === "failed" || progress.status === "cancelled";
  const isRunning = !isTerminal && progress.status !== "pending";

  return (
    <div className="space-y-6">
      <SectionHeading
        eyebrow="Live Job"
        title={job?.title ?? `Job ${params.id.slice(0, 8)}...`}
        description="Streaming progress updates from the backend processing pipeline."
      />

      <JobProgress progress={progress} />

      {/* Action buttons */}
      <div className="flex flex-wrap gap-3">
        {isRunning && (
          <button
            onClick={handleCancel}
            className="inline-flex items-center gap-2 rounded-lg border border-rose-400/30 px-4 py-2 text-sm text-rose-300 hover:bg-rose-400/10"
          >
            <XCircle className="h-4 w-4" />
            Cancel Job
          </button>
        )}
        {(progress.status === "failed" || progress.status === "cancelled") && (
          <button
            onClick={handleRetry}
            disabled={retrying}
            className="inline-flex items-center gap-2 rounded-lg bg-cyan-300/20 px-4 py-2 text-sm text-cyan-50 hover:bg-cyan-300/30"
          >
            <RefreshCw className={`h-4 w-4 ${retrying ? "animate-spin" : ""}`} />
            {retrying ? "Retrying..." : "Retry with Same Settings"}
          </button>
        )}
        {progress.status === "completed" && job?.video_id && (
          <a
            href={`${API_URL}/api/v1/videos/${job.video_id}/download`}
            className="inline-flex items-center gap-2 rounded-lg bg-linear-to-r from-teal-300 to-orange-300 px-4 py-2 text-sm font-semibold text-slate-950"
          >
            <Download className="h-4 w-4" />
            Download Video
          </a>
        )}
      </div>

      {/* Error message */}
      {progress.status === "failed" && job?.error_message && (
        <div className="surface border-rose-400/30 p-4">
          <p className="text-sm font-medium text-rose-300">Error Details</p>
          <p className="mt-1 text-sm text-rose-200/70">{job.error_message}</p>
        </div>
      )}

      {/* Video preview */}
      <section className="surface p-5">
        <h2 className="text-lg font-semibold">Output Preview</h2>
        {progress.status === "completed" && job?.video_id ? (
          <video
            controls
            autoPlay
            className="mt-4 aspect-video w-full rounded-xl bg-black"
            src={`${API_URL}/api/v1/videos/${job.video_id}/stream`}
          />
        ) : (
          <div className="mt-4 flex aspect-video items-center justify-center rounded-xl border border-cyan-300/20 bg-slate-900/70">
            <p className="text-sm text-cyan-100/40">
              {progress.status === "failed" ? "Generation failed" : "Video will appear here when ready"}
            </p>
          </div>
        )}
      </section>

      {/* Job metadata */}
      {job && (
        <section className="surface p-5">
          <h2 className="text-lg font-semibold">Job Details</h2>
          <div className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
            <div><span className="text-cyan-100/50">Source:</span> <span className="text-cyan-50">{job.source_type.replace("_", " + ")}</span></div>
            <div><span className="text-cyan-100/50">Created:</span> <span className="text-cyan-50">{new Date(job.created_at).toLocaleString()}</span></div>
            {job.settings && (
              <>
                <div><span className="text-cyan-100/50">Voice:</span> <span className="text-cyan-50">{(job.settings as any).voice ?? "—"}</span></div>
                <div><span className="text-cyan-100/50">Resolution:</span> <span className="text-cyan-50">{(job.settings as any).resolution ?? "—"}</span></div>
                <div><span className="text-cyan-100/50">FPS:</span> <span className="text-cyan-50">{(job.settings as any).fps ?? "—"}</span></div>
                <div><span className="text-cyan-100/50">AI Backgrounds:</span> <span className="text-cyan-50">{(job.settings as any).generate_backgrounds ? "Yes" : "No"}</span></div>
              </>
            )}
            {job.started_at && job.completed_at && (
              <div className="sm:col-span-2">
                <span className="text-cyan-100/50">Render time:</span>{" "}
                <span className="text-cyan-50">
                  {Math.round((new Date(job.completed_at).getTime() - new Date(job.started_at).getTime()) / 1000)}s
                </span>
              </div>
            )}
          </div>
        </section>
      )}
    </div>
  );
}
