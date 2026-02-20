"use client";

import { motion } from "framer-motion";
import { CheckCircle2, LoaderCircle } from "lucide-react";

import { JobProgress as JobProgressType } from "@/types/job";
import { formatPercent } from "@/lib/utils";

export function JobProgress({ progress }: { progress: JobProgressType }) {
  return (
    <div className="surface p-5">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          {progress.status === "completed" ? (
            <CheckCircle2 className="h-5 w-5 text-emerald-400" />
          ) : (
            <LoaderCircle className="h-5 w-5 animate-spin text-cyan-300" />
          )}
          <p className="font-medium">{progress.step}</p>
        </div>
        <p className="text-sm text-cyan-100/70">{formatPercent(progress.progress)}</p>
      </div>

      <div className="h-3 overflow-hidden rounded-full bg-cyan-950/70">
        <motion.div
          animate={{ width: `${Math.max(4, progress.progress * 100)}%` }}
          transition={{ duration: 0.6 }}
          className="shimmer h-full rounded-full bg-gradient-to-r from-teal-300 via-cyan-300 to-orange-300"
        />
      </div>
    </div>
  );
}
