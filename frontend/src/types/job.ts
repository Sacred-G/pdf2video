export type JobStatus =
  | "pending"
  | "classifying"
  | "scripting"
  | "voiceover"
  | "backgrounds"
  | "composing"
  | "exporting"
  | "completed"
  | "failed"
  | "cancelled";

export interface JobProgress {
  status: JobStatus;
  step: string;
  progress: number;
}

export interface Job {
  id: string;
  title: string;
  source_type: "pdf" | "text_images";
  status: JobStatus;
  created_at: string;
  progress: number;
  current_step: string;
  error_message?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  video_id?: string | null;
  settings?: Record<string, unknown>;
}
