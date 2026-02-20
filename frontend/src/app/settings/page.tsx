export default function SettingsPage() {
  return (
    <div className="grid gap-5 lg:grid-cols-2">
      <section className="surface p-5">
        <p className="text-xs uppercase tracking-[0.2em] text-cyan-200/70">Profile</p>
        <h1 className="mt-2 text-2xl font-semibold">Account Settings</h1>
        <div className="mt-4 space-y-3">
          <input className="w-full rounded-xl border border-cyan-200/20 bg-cyan-950/40 p-3" defaultValue="You" />
          <input className="w-full rounded-xl border border-cyan-200/20 bg-cyan-950/40 p-3" defaultValue="you@example.com" />
        </div>
      </section>

      <section className="surface p-5">
        <p className="text-xs uppercase tracking-[0.2em] text-cyan-200/70">API Key</p>
        <h2 className="mt-2 text-xl font-semibold">OpenAI Credential</h2>
        <input
          type="password"
          placeholder="sk-..."
          className="mt-4 w-full rounded-xl border border-cyan-200/20 bg-cyan-950/40 p-3"
        />
        <button className="mt-4 rounded-lg bg-gradient-to-r from-teal-400 to-orange-300 px-4 py-2 font-semibold text-slate-950">
          Save Securely
        </button>
      </section>
    </div>
  );
}
