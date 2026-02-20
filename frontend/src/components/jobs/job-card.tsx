import Link from "next/link";
import { ArrowUpRight } from "lucide-react";

import { Job } from "@/types/job";
import { cn, formatDate } from "@/lib/utils";

const statusColor: Record<Job["status"], string> = {
  pending: "bg-slate-500/20 text-slate-100",
  classifying: "bg-cyan-500/20 text-cyan-100",
  scripting: "bg-violet-500/20 text-violet-100",
  voiceover: "bg-amber-500/20 text-amber-100",
  backgrounds: "bg-fuchsia-500/20 text-fuchsia-100",
  composing: "bg-indigo-500/20 text-indigo-100",
  exporting: "bg-orange-500/20 text-orange-100",
  completed: "bg-emerald-500/20 text-emerald-100",
  failed: "bg-rose-500/20 text-rose-100",
  cancelled: "bg-zinc-500/20 text-zinc-100"
};

export function JobCard({ job }: { job: Job }) {
  return (
    <article className="surface p-4 transition hover:border-cyan-300/40">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-cyan-200/70">{job.source_type.replace("_", " + ")}</p>
          <h3 className="mt-1 text-lg font-semibold">{job.title}</h3>
        </div>
        <span className={cn("rounded-full px-3 py-1 text-xs capitalize", statusColor[job.status])}>{job.status}</span>
      </div>
      <p className="text-sm text-cyan-50/65">{formatDate(job.created_at)}</p>
      <div className="mt-4 flex items-center justify-between text-sm">
        <p className="text-cyan-100/70">{Math.round(job.progress * 100)}% complete</p>
        <Link className="inline-flex items-center gap-1 text-cyan-200 hover:text-white" href={`/jobs/${job.id}`}>
          Open
          <ArrowUpRight className="h-4 w-4" />
        </Link>
      </div>
    </article>
  );
}
