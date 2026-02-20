"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";

import { JobList } from "@/components/jobs/job-list";
import { SectionHeading } from "@/components/shared/section-heading";
import { VideoGallery } from "@/components/video/video-gallery";
import { apiFetch } from "@/lib/api-client";
import { mockJobs, mockVideos } from "@/lib/mock-data";
import { Job } from "@/types/job";
import { Video } from "@/types/video";

interface JobListResponse { items: Job[]; total: number }
interface VideoListResponse { items: Video[]; total: number }

export default function DashboardPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [videos, setVideos] = useState<Video[]>([]);
  const [jobTotal, setJobTotal] = useState(0);
  const [videoTotal, setVideoTotal] = useState(0);

  useEffect(() => {
    apiFetch<JobListResponse>("/api/v1/jobs?page=1&page_size=6")
      .then((res) => { setJobs(res.items); setJobTotal(res.total); })
      .catch(() => { setJobs(mockJobs); setJobTotal(mockJobs.length); });
    apiFetch<VideoListResponse>("/api/v1/videos?page=1&page_size=6")
      .then((res) => { setVideos(res.items); setVideoTotal(res.total); })
      .catch(() => { setVideos(mockVideos); setVideoTotal(mockVideos.length); });
  }, []);

  const stats = [
    { label: "Videos Generated", value: String(videoTotal) },
    { label: "Total Jobs", value: String(jobTotal) },
    { label: "GPU Engine", value: "NVENC" },
    { label: "Success Rate", value: jobTotal > 0 ? `${Math.round((jobs.filter(j => j.status === "completed").length / Math.max(jobs.length, 1)) * 100)}%` : "—" },
  ];

  return (
    <div className="space-y-8">
      <SectionHeading
        eyebrow="Command Center"
        title="Build cinematic videos from documents in minutes"
        description="Track job status in real-time, tune style presets, and publish polished results from a modern production dashboard."
      />

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {stats.map((item, index) => (
          <motion.article
            key={item.label}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.08 }}
            className="surface soft-grid p-4"
          >
            <p className="text-xs uppercase tracking-[0.2em] text-cyan-100/70">{item.label}</p>
            <p className="mt-3 text-3xl font-semibold">{item.value}</p>
          </motion.article>
        ))}
      </section>

      <section className="space-y-4">
        <SectionHeading title="Recent Jobs" description="Live queue and processing status." />
        {jobs.length > 0 ? (
          <JobList jobs={jobs} />
        ) : (
          <p className="text-sm text-cyan-100/60">No jobs yet. Create your first video!</p>
        )}
      </section>

      <section className="space-y-4">
        <SectionHeading title="Latest Videos" description="Ready to preview, download, or share." />
        {videos.length > 0 ? (
          <VideoGallery videos={videos} />
        ) : (
          <p className="text-sm text-cyan-100/60">No videos yet.</p>
        )}
      </section>
    </div>
  );
}
