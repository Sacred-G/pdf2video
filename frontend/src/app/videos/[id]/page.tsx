"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Download } from "lucide-react";

import { SectionHeading } from "@/components/shared/section-heading";
import { VideoPlayer } from "@/components/video/video-player";
import { apiFetch } from "@/lib/api-client";
import { formatDuration } from "@/lib/utils";

interface VideoMeta {
  id: string;
  title: string;
  duration_seconds: number;
  resolution: string;
  file_size: number;
  created_at: string;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function VideoDetailPage() {
  const params = useParams<{ id: string }>();
  const [video, setVideo] = useState<VideoMeta | null>(null);

  useEffect(() => {
    apiFetch<VideoMeta>(`/api/v1/videos/${params.id}`)
      .then(setVideo)
      .catch(() => {});
  }, [params.id]);

  return (
    <div className="space-y-6">
      <SectionHeading
        eyebrow="Playback"
        title={video?.title ?? `Video ${params.id}`}
        description="Watch generated output, inspect metadata, and share your result."
      />
      <div className="surface p-5">
        <VideoPlayer
          src={`${API_URL}/api/v1/videos/${params.id}/stream`}
          title={video?.title}
          downloadUrl={`${API_URL}/api/v1/videos/${params.id}/download`}
        />
        {video && (
          <div className="mt-4 flex flex-wrap items-center gap-4 text-sm text-cyan-100/70">
            <span>{video.resolution}</span>
            <span>{formatDuration(video.duration_seconds)}</span>
            <span>{(video.file_size / (1024 * 1024)).toFixed(1)} MB</span>
          </div>
        )}
        <div className="mt-4 flex gap-3">
          <a
            href={`${API_URL}/api/v1/videos/${params.id}/download`}
            className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-teal-400 to-orange-300 px-4 py-2 font-semibold text-slate-950"
          >
            <Download className="h-4 w-4" />
            Download
          </a>
        </div>
      </div>
    </div>
  );
}
