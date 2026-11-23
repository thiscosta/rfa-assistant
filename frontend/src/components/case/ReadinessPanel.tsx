"use client";

import { useState } from "react";
import type { FormSchema, Issue } from "@/lib/api";

export function ReadinessPanel({ issues, schema }: { issues: Issue[]; schema: FormSchema }) {
  const [showAllIssues, setShowAllIssues] = useState(false);
  const errors = issues.filter((i) => i.severity === "error");
  const warnings = issues.filter((i) => i.severity === "warning");
  const shown = showAllIssues ? issues : issues.slice(0, 6);
  const labelOf = (key: string | null) => schema.fields.find((f) => f.key === key)?.label.replace(/[:?]$/, "") ?? key;

  return (
  <div className="card p-3">
    <div className="mb-2 flex items-center justify-between">
      <h2 className="text-sm font-semibold text-slate-900">Readiness</h2>
      <span className="text-xs text-slate-500">
        <span className={errors.length ? "text-rose-700" : "text-emerald-700"}>{errors.length} to fix</span> ·{" "}
        {warnings.length} to check
      </span>
    </div>
    {issues.length === 0 ? (
      <p className="text-sm text-emerald-700">Everything required is filled in.</p>
    ) : (
      <ul className="space-y-1">
        {shown.map((i, n) => (
          <li key={n}>
            <button
              className="w-full text-left text-xs hover:underline"
              onClick={() => i.field && document.getElementById(`field-${i.field}`)?.scrollIntoView({ behavior: "smooth", block: "center" })}
            >
              <span className={i.severity === "error" ? "text-rose-700" : "text-amber-800"}>
                {i.severity === "error" ? "●" : "○"}{" "}
              </span>
              {i.field && !i.message.includes(labelOf(i.field) ?? "") && (
                <span className="font-medium text-slate-700">{labelOf(i.field)}: </span>
              )}
              <span className="text-slate-600">{i.message}</span>
            </button>
          </li>
        ))}
      </ul>
    )}
    {issues.length > 6 && (
      <button className="mt-1 text-xs text-ink underline" onClick={() => setShowAllIssues(!showAllIssues)}>
        {showAllIssues ? "Show fewer" : `Show all ${issues.length}`}
      </button>
    )}
  </div>
  );
}
