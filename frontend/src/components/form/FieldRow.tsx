"use client";

import { useEffect, useRef, useState } from "react";
import type { CaseView, FieldState, FormFieldDef, Issue } from "@/lib/api";
import { SignatureControl } from "./SignatureControl";
import { SOURCE, type OpenEvidence } from "./sources";

export function FieldRow({
  def,
  state,
  issues,
  onSave,
  onReset,
  onEvidence,
  signature,
}: {
  def: FormFieldDef;
  state: FieldState | undefined;
  issues: Issue[];
  onSave: (value: string) => void;
  onReset: () => void;
  onEvidence: OpenEvidence;
  signature?: { view: CaseView; onChange: (fn: () => Promise<CaseView>) => void };
}) {
  const s: FieldState = state ?? { value: "", source: "empty", evidence: [], note: null, uncertain: false, alternatives: [] };
  const [draft, setDraft] = useState(s.value);
  const focused = useRef(false);

  useEffect(() => {
    if (!focused.current) setDraft(s.value);
  }, [s.value]);

  const commit = () => {
    focused.current = false;
    if (draft !== s.value) onSave(draft);
  };
  const missing = def.required && !s.value.trim();
  const badge = missing ? { label: "Missing", cls: "bg-rose-50 text-rose-700", title: "Required on the form" } : SOURCE[s.source];
  const id = `f-${def.key}`;
  const common = {
    id,
    value: draft,
    onFocus: () => (focused.current = true),
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setDraft(e.target.value),
    onBlur: commit,
  };

  return (
    <div
      id={`field-${def.key}`}
      className={`grid gap-x-4 gap-y-1 px-4 py-3 ${def.kind === "longtext" ? "" : "md:grid-cols-[220px_1fr]"}`}
    >
      <label htmlFor={id} className="pt-1.5 text-sm font-medium text-slate-700">
        {def.label.replace(/:$/, "")}
        {def.required && <span className="text-rose-600"> *</span>}
        {def.help && <span className="mt-0.5 block text-xs font-normal text-slate-500">{def.help}</span>}
      </label>
      <div className="min-w-0 space-y-1.5">
        <div className="flex items-start gap-2">
          <div className="min-w-0 flex-1">
            {signature ? (
              <SignatureControl view={signature.view} onChange={signature.onChange} />
            ) : def.kind === "choice" ? (
              <select
                id={id}
                className="input"
                value={s.value}
                onChange={(e) => {
                  setDraft(e.target.value);
                  onSave(e.target.value);
                }}
              >
                <option value="">Select…</option>
                {def.choices.map((c) => (
                  <option key={c}>{c}</option>
                ))}
              </select>
            ) : def.kind === "longtext" ? (
              <textarea {...common} rows={Math.max(3, def.lines + 1)} className="input font-mono text-[13px] leading-5" />
            ) : (
              <input {...common} className={`input ${s.uncertain ? "border-amber-400" : ""}`} placeholder={def.kind === "date" ? "MM/DD/YYYY" : ""} />
            )}
          </div>
          <span className={`mt-1 shrink-0 rounded-full px-2 py-0.5 text-[11px] font-medium ${badge.cls}`} title={badge.title}>
            {badge.label}
          </span>
        </div>

        {s.uncertain && s.source !== "user" && (
          <p className="text-xs text-amber-800">Hard to read in the source. Check it against the document.</p>
        )}
        {s.note && <p className="text-xs text-slate-500">{s.note}</p>}
        {issues
          .filter((i) => !(i.message.endsWith("is required.") && missing))
          .filter((i) => !i.message.startsWith("Read from a hard-to-read") && !i.message.startsWith("Documents disagree"))
          .map((i, n) => (
            <p key={n} className={`text-xs ${i.severity === "error" ? "text-rose-700" : "text-amber-800"}`}>
              {i.message}
            </p>
          ))}

        {s.alternatives.length > 0 && (
          <div className="rounded-md border border-amber-200 bg-amber-50 p-2 text-xs">
            <div className="mb-1 font-medium text-amber-900">Other documents say:</div>
            {s.alternatives.map((a, n) => (
              <div key={n} className="flex flex-wrap items-center gap-2">
                <span className="font-mono text-amber-950">{a.value}</span>
                <button className="text-ink underline" onClick={() => onEvidence(a.evidence)}>
                  {a.evidence.doc_name}
                </button>
                <button className="btn-ghost px-1.5 py-0.5 text-xs" onClick={() => onSave(a.value)}>
                  Use this
                </button>
              </div>
            ))}
          </div>
        )}

        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          {s.evidence.map((e, n) => (
            <button key={n} onClick={() => onEvidence(e)} className="max-w-full truncate text-xs text-ink hover:underline" title={e.quote}>
              ↗ {e.doc_name}
            </button>
          ))}
          {s.source === "user" && def.key !== "signature" && (
            <button onClick={onReset} className="text-xs text-slate-500 underline hover:text-slate-700">
              Undo edit (fill automatically)
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
