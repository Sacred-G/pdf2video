"use client";

import { useEffect, useState } from "react";

import { SectionHeading } from "@/components/shared/section-heading";
import { VideoGallery } from "@/components/video/video-gallery";
import { apiFetch } from "@/lib/api-client";
import { Video } from "@/types/video";

interface VideoListResponse { items: Video[]; total: number }

export default function VideosPage() {
  const [videos, setVideos] = useState<Video[]>([]);

  useEffect(() => {
    apiFetch<VideoListResponse>("/api/v1/videos?page=1&page_size=50")
      .then((res) => setVideos(res.items))
      .catch(() => {});
  }, []);

  return (
    <div className="space-y-6">
      <SectionHeading
        eyebrow="Media Library"
        title="Video gallery"
        description="Browse generated assets, sort by date, and open playback details."
      />
      {videos.length > 0 ? (
        <VideoGallery videos={videos} />
      ) : (
        <p className="text-sm text-cyan-100/60">No videos yet. Generate your first one!</p>
      )}
    </div>
  );
}
