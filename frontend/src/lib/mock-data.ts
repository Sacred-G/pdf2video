import { Job } from "@/types/job";
import { Video } from "@/types/video";

export const mockJobs: Job[] = [
  {
    id: "job_01",
    title: "Q4 Market Trends Deck",
    source_type: "pdf",
    status: "composing",
    created_at: "2026-02-20T10:00:00Z",
    progress: 0.72,
    current_step: "Composing video"
  },
  {
    id: "job_02",
    title: "Product Launch Story",
    source_type: "text_images",
    status: "completed",
    created_at: "2026-02-19T15:10:00Z",
    progress: 1,
    current_step: "Complete",
    video_id: "vid_02"
  },
  {
    id: "job_03",
    title: "Investor Update",
    source_type: "pdf",
    status: "failed",
    created_at: "2026-02-19T09:30:00Z",
    progress: 0.41,
    current_step: "Voiceover"
  }
];

export const mockVideos: Video[] = [
  {
    id: "vid_01",
    title: "Q4 Highlights",
    created_at: "2026-02-19T18:30:00Z",
    duration_seconds: 94,
    resolution: "1920x1080",
    thumbnail_url: "https://images.unsplash.com/photo-1516321165247-4aa89a48be28?q=80&w=1400&auto=format&fit=crop",
    file_size: 128 * 1024 * 1024
  },
  {
    id: "vid_02",
    title: "Product Launch Story",
    created_at: "2026-02-19T16:00:00Z",
    duration_seconds: 122,
    resolution: "2560x1440",
    thumbnail_url: "https://images.unsplash.com/photo-1522071820081-009f0129c71c?q=80&w=1400&auto=format&fit=crop",
    file_size: 210 * 1024 * 1024
  },
  {
    id: "vid_03",
    title: "Operations Review",
    created_at: "2026-02-18T12:22:00Z",
    duration_seconds: 76,
    resolution: "1920x1080",
    thumbnail_url: "https://images.unsplash.com/photo-1460925895917-afdab827c52f?q=80&w=1400&auto=format&fit=crop",
    file_size: 103 * 1024 * 1024
  }
];
