export interface Video {
  id: string;
  title: string;
  created_at: string;
  duration_seconds: number;
  resolution: string;
  thumbnail_url: string | null;
  file_size: number;
}
