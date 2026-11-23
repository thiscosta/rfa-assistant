"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, type CaseSummary } from "@/lib/api";

export default function CasesPage() {
  const router = useRouter();
  const [cases, setCases] = useState<CaseSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [label, setLabel] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    api.cases().then(setCases).catch((e) => setError(e.message));
  }, []);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setCreating(true);
    try {
      const c = await api.createCase(label);
      router.push(`/cases/${c.id}`);
    } catch (err) {
      setError((err as Error).message);
      setCreating(false);
    }
  }

  async function remove(id: string) {
    if (!confirm("Delete this request and its uploaded documents? This can't be undone.")) return;
    await api.deleteCase(id);
    setCases((cs) => cs?.filter((c) => c.id !== id) ?? null);
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Requests for approval of services</h1>
        <p className="mt-1 text-sm text-slate-600">
          Start a request, drop in the patient&apos;s documents (referral, intake form, notes, insurance card, labs), review
          what was found, and download the completed form.
        </p>
      </div>

      <form onSubmit={create} className="card flex flex-wrap items-end gap-3 p-4">
        <label className="min-w-64 flex-1 text-sm">
          <span className="mb-1 block font-medium text-slate-700">New request</span>
          <input
            className="input"
            placeholder="Label, e.g. patient initials or referral #"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
          />
        </label>
        <button className="btn-primary" disabled={creating}>
          {creating ? "Creating…" : "Start request"}
        </button>
      </form>

      {error && <p className="rounded-md bg-rose-50 p-3 text-sm text-rose-700">{error}</p>}

      <div className="card divide-y divide-slate-100">
        {cases === null && !error && <p className="p-4 text-sm text-slate-500">Loading…</p>}
        {cases?.length === 0 && <p className="p-6 text-center text-sm text-slate-500">No requests yet.</p>}
        {cases?.map((c) => (
          <div key={c.id} className="flex items-center gap-4 p-4">
            <Link href={`/cases/${c.id}`} className="min-w-0 flex-1">
              <div className="truncate font-medium text-ink">{c.member_name || c.label}</div>
              <div className="truncate text-xs text-slate-500">
                {[c.member_name ? c.label : null, c.payer, `${c.documents} document${c.documents === 1 ? "" : "s"}`]
                  .filter(Boolean)
                  .join(" · ")}
              </div>
            </Link>
            {c.errors > 0 ? (
              <span className="rounded-full bg-rose-50 px-2 py-0.5 text-xs text-rose-700">{c.errors} to fix</span>
            ) : (
              <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-xs text-emerald-700">Ready</span>
            )}
            <span className="hidden text-xs text-slate-400 sm:block">{new Date(c.updated_at).toLocaleString()}</span>
            <button className="btn-ghost text-xs" onClick={() => remove(c.id)}>
              Delete
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
