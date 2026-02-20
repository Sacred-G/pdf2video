"use client";

import { useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { toast } from "sonner";

import { useAuth } from "@/hooks/use-auth";

export default function RegisterPage() {
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      toast.error("Please fill in all fields");
      return;
    }
    setLoading(true);
    try {
      await register({ email, password, displayName });
      toast.success("Account created!");
    } catch (err: any) {
      toast.error(err?.message ?? err?.detail ?? "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center p-4">
      <motion.section
        initial={{ opacity: 0, scale: 0.98 }}
        animate={{ opacity: 1, scale: 1 }}
        className="surface w-full max-w-md space-y-4 p-6"
      >
        <p className="text-xs uppercase tracking-[0.2em] text-cyan-200/70">Get started</p>
        <h1 className="text-3xl font-semibold">Create account</h1>
        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            placeholder="Display name"
            autoComplete="name"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            className="w-full rounded-xl border border-cyan-200/20 bg-cyan-950/40 p-3"
          />
          <input
            placeholder="Email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded-xl border border-cyan-200/20 bg-cyan-950/40 p-3"
          />
          <input
            type="password"
            placeholder="Password"
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-xl border border-cyan-200/20 bg-cyan-950/40 p-3"
          />
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-xl bg-gradient-to-r from-teal-300 to-orange-300 px-4 py-3 font-semibold text-slate-950 disabled:opacity-50"
          >
            {loading ? "Creating account..." : "Register"}
          </button>
        </form>
        <p className="text-sm text-cyan-100/70">
          Already have an account? <Link href="/login" className="text-cyan-200 underline">Sign in</Link>
        </p>
      </motion.section>
    </main>
  );
}
