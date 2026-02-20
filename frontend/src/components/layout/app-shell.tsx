"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { AppSidebar } from "@/components/layout/app-sidebar";
import { Header } from "@/components/layout/header";
import { navItems } from "@/lib/constants";

const authRoutes = new Set(["/login", "/register"]);

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const isAuthRoute = authRoutes.has(pathname);

  if (isAuthRoute) {
    return <main className="min-h-screen">{children}</main>;
  }

  return (
    <div className="min-h-screen md:grid md:grid-cols-[260px_1fr]">
      <AppSidebar />
      <div className="p-4 md:p-8">
        <nav className="surface mb-4 flex gap-2 overflow-auto p-2 md:hidden">
          {navItems.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={active ? "rounded-lg bg-cyan-300/20 px-3 py-2 text-sm" : "rounded-lg px-3 py-2 text-sm text-cyan-100/70"}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
        <Header />
        <main className="mt-5">{children}</main>
      </div>
    </div>
  );
}
