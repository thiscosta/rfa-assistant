"use client";

import { useState } from "react";
import { api, type CaseView } from "@/lib/api";

export function NarrativeBanner({ view, onChange }: { view: CaseView; onChange: (v: CaseView) => void }) {
  const [err, setErr] = useState<string | null>(null);
  const gaps = view.narrative_status === "done" ? (view.narrative_draft?.unsupported_gaps ?? []) : [];
  return (
    <div className="border-b border-slate-100 bg-slate-50 px-4 py-2 text-xs text-slate-600">
    <div className="flex items-center gap-3">
      <span className="flex-1">
        {view.narrative_status === "drafting"
          ? "Claude is drafting Sections E and F from the documents…"
          : view.narrative_status === "failed"
            ? `Drafting failed: ${view.narrative_error}. Use Redraft to try again.`
            : view.narrative_status === "done"
              ? "Sections E and F were drafted by Claude from the document facts. Edit before signing."
              : "Claude drafts Sections E and F once all documents are read."}
      </span>
      {err && <span className="text-rose-700">{err}</span>}
      <button
        className="btn-secondary text-xs"
        disabled={view.narrative_status === "drafting"}
        onClick={() =>
          api
            .redraft(view.id)
            .then(onChange)
            .catch((e) => setErr(e.message))
        }
      >
        Redraft with AI
      </button>
    </div>
      {gaps.length > 0 && (
        <details className="mt-1.5">
          <summary className="cursor-pointer text-amber-800">
            {gaps.length} thing{gaps.length === 1 ? "" : "s"} a payer reviewer may ask for that the documents don&apos;t say
          </summary>
          <ul className="mt-1 list-disc space-y-0.5 pl-5 text-slate-700">
            {gaps.map((g, i) => (
              <li key={i}>{g}</li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
