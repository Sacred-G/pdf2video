import { Video } from "@/types/video";
import { VideoCard } from "@/components/video/video-card";

export function VideoGallery({ videos }: { videos: Video[] }) {
  return (
    <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {videos.map((video) => (
        <VideoCard key={video.id} video={video} />
      ))}
    </section>
  );
}
