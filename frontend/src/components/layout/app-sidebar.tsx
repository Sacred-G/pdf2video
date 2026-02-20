"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Film, Gauge, Settings, Sparkles, Workflow } from "lucide-react";

import { cn } from "@/lib/utils";

const items = [
  { href: "/", label: "Dashboard", icon: Gauge },
  { href: "/create", label: "Create Job", icon: Sparkles },
  { href: "/jobs", label: "Jobs", icon: Workflow },
  { href: "/videos", label: "Videos", icon: Film },
  { href: "/settings", label: "Settings", icon: Settings }
];

export function AppSidebar() {
  const pathname = usePathname();

  return (
    <aside className="surface sticky top-0 hidden h-screen rounded-none border-l-0 border-t-0 border-b-0 p-6 md:block">
      <div className="mb-8">
        <p className="text-xs uppercase tracking-[0.25em] text-cyan-200/80">PDF2Video</p>
        <h1 className="mt-2 text-2xl font-semibold">Studio Control</h1>
      </div>

      <nav className="space-y-2">
        {items.map((item) => {
          const active = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "group flex items-center gap-3 rounded-xl border border-transparent px-4 py-3 text-sm text-cyan-100/80 transition",
                active
                  ? "border-cyan-300/40 bg-cyan-300/10 text-white"
                  : "hover:border-cyan-400/30 hover:bg-cyan-500/10"
              )}
            >
              <item.icon className={cn("h-4 w-4", active ? "text-cyan-200" : "text-cyan-50/70")} />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="surface mt-8 p-4 text-sm">
        <p className="text-cyan-100/70">GPU Engine</p>
        <p className="mt-1 font-medium">NVENC Ready</p>
        <p className="mt-2 text-xs text-cyan-100/60">4 jobs active capacity with your hardware profile.</p>
      </div>
    </aside>
  );
}
