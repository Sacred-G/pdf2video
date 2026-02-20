import Image from "next/image";
import Link from "next/link";
import { Film, PlayCircle } from "lucide-react";

import { Video } from "@/types/video";
import { formatDate, formatDuration } from "@/lib/utils";

export function VideoCard({ video }: { video: Video }) {
  const sizeMb = (video.file_size / (1024 * 1024)).toFixed(1);

  return (
    <article className="surface overflow-hidden">
      <div className="relative flex h-44 items-center justify-center bg-slate-900/60">
        {video.thumbnail_url ? (
          <Image src={video.thumbnail_url} alt={video.title} fill sizes="(max-width: 768px) 100vw, (max-width: 1280px) 50vw, 33vw" className="object-cover" />
        ) : (
          <Film className="h-10 w-10 text-cyan-200/30" />
        )}
      </div>
      <div className="p-4">
        <p className="text-xs uppercase tracking-[0.2em] text-cyan-200/70">{video.resolution}</p>
        <h3 className="mt-1 text-lg font-semibold">{video.title}</h3>
        <p className="mt-1 text-sm text-cyan-100/70">
          {formatDate(video.created_at)} • {formatDuration(video.duration_seconds)} • {sizeMb} MB
        </p>
        <Link href={`/videos/${video.id}`} className="mt-3 inline-flex items-center gap-2 text-cyan-200 hover:text-white">
          <PlayCircle className="h-4 w-4" />
          Watch
        </Link>
      </div>
    </article>
  );
}
