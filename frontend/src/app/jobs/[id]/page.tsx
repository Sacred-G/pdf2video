"use client";

import { useParams } from "next/navigation";

import { JobProgress } from "@/components/jobs/job-progress";
import { SectionHeading } from "@/components/shared/section-heading";
import { useJobProgress } from "@/hooks/use-job-progress";

export default function JobDetailPage() {
  const params = useParams<{ id: string }>();
  const progress = useJobProgress(params.id);

  return (
    <div className="space-y-6">
      <SectionHeading
        eyebrow="Live Job"
        title={`Job ${params.id}`}
        description="Streaming progress updates from the backend processing pipeline."
      />
      <JobProgress progress={progress} />
      <section className="surface p-5">
        <h2 className="text-lg font-semibold">Output Preview</h2>
        <div className="mt-4 aspect-video rounded-xl border border-cyan-300/20 bg-slate-900/70" />
      </section>
    </div>
  );
}
