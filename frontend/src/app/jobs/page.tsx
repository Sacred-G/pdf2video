"use client";

import { useEffect, useState } from "react";

import { JobList } from "@/components/jobs/job-list";
import { SectionHeading } from "@/components/shared/section-heading";
import { apiFetch } from "@/lib/api-client";
import { Job } from "@/types/job";

interface JobListResponse { items: Job[]; total: number }

const filters = [
  { label: "All", value: "" },
  { label: "Running", value: "composing" },
  { label: "Completed", value: "completed" },
  { label: "Failed", value: "failed" },
];

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [activeFilter, setActiveFilter] = useState("");

  useEffect(() => {
    const params = new URLSearchParams({ page: "1", page_size: "50" });
    if (activeFilter) params.set("status_filter", activeFilter);
    apiFetch<JobListResponse>(`/api/v1/jobs?${params}`)
      .then((res) => setJobs(res.items))
      .catch(() => {});
  }, [activeFilter]);

  return (
    <div className="space-y-6">
      <SectionHeading
        eyebrow="Pipeline Queue"
        title="All jobs"
        description="Filter, inspect, retry, and manage generation runs."
      />
      <div className="surface flex flex-wrap items-center gap-3 p-3 text-sm text-cyan-100/80">
        {filters.map((f) => (
          <button
            key={f.value}
            onClick={() => setActiveFilter(f.value)}
            className={`rounded-lg px-3 py-1 ${activeFilter === f.value ? "bg-cyan-400/20" : "hover:bg-cyan-400/10"}`}
          >
            {f.label}
          </button>
        ))}
      </div>
      {jobs.length > 0 ? (
        <JobList jobs={jobs} />
      ) : (
        <p className="text-sm text-cyan-100/60">No jobs found.</p>
      )}
    </div>
  );
}
