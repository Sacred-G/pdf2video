"use client";

import Link from "next/link";
import { Bell, Plus } from "lucide-react";
import { motion } from "framer-motion";

import { NavUser } from "@/components/layout/nav-user";
import { ThemeToggle } from "@/components/layout/theme-toggle";

export function Header() {
  return (
    <motion.header
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="surface flex items-center justify-between gap-3 px-4 py-3"
    >
      <div>
        <p className="text-xs uppercase tracking-[0.2em] text-cyan-200/70">Production Workspace</p>
        <h2 className="text-xl font-semibold">Cinematic Generation Pipeline</h2>
      </div>
      <div className="flex items-center gap-2">
        <ThemeToggle />
        <button className="rounded-lg border border-cyan-200/30 p-2 text-cyan-100/80 transition hover:bg-cyan-300/10">
          <Bell className="h-4 w-4" />
        </button>
        <Link
          href="/create"
          className="inline-flex items-center gap-2 rounded-lg bg-linear-to-r from-teal-400 to-orange-400 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:brightness-110"
        >
          <Plus className="h-4 w-4" />
          New Video Job
        </Link>
        <NavUser />
      </div>
    </motion.header>
  );
}
