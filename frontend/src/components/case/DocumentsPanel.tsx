"use client";

import { useRef, useState } from "react";
import { api, type CaseDocument, type CaseView } from "@/lib/api";
import { DOC_TYPE_LABELS } from "@/lib/labels";

const STATUS: Record<CaseDocument["status"], { label: string; cls: string }> = {
  queued: { label: "Waiting", cls: "bg-slate-100 text-slate-600" },
  processing: { label: "Claude is reading…", cls: "bg-sky-50 text-sky-700 animate-pulse" },
  extracted: { label: "Read", cls: "bg-emerald-50 text-emerald-700" },
  failed: { label: "Failed", cls: "bg-rose-50 text-rose-700" },
};

export function DocumentsPanel({
  view,
  onChange,
  onOpen,
}: {
  view: CaseView;
  onChange: (v: CaseView) => void;
  onOpen: (doc: CaseDocument) => void;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function upload(files: File[]) {
    if (!files.length) return;
    setBusy(true);
    setError(null);
    try {
      onChange(await api.upload(view.id, files));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function act(fn: () => Promise<CaseView>) {
    try {
      onChange(await fn());
    } catch (e) {
      setError((e as Error).message);
    }
  }

  const groups = view.patient_groups;
  const primary =
    groups.find((g) => view.documents.some((d) => d.included && d.patient_key && g.doc_ids.includes(d.id)))?.key ?? null;

  return (
    <div className="space-y-3">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          upload(Array.from(e.dataTransfer.files));
        }}
        onClick={() => input.current?.click()}
        className={`cursor-pointer rounded-lg border-2 border-dashed p-5 text-center transition ${
          dragging ? "border-ink-soft bg-sky-50" : "border-slate-300 bg-white hover:border-slate-400"
        }`}
      >
        <input
          ref={input}
          type="file"
          multiple
          accept="application/pdf,image/png,image/jpeg"
          className="hidden"
          onChange={(e) => {
            upload(Array.from(e.target.files ?? []));
            e.target.value = "";
          }}
        />
        <div className="text-sm font-medium text-slate-700">{busy ? "Uploading…" : "Drop documents here or click to add"}</div>
        <div className="mt-1 text-xs text-slate-500">PDF, PNG or JPEG: referrals, intake forms, notes, insurance cards, labs</div>
      </div>

      {error && <p className="rounded-md bg-rose-50 p-2 text-xs text-rose-700">{error}</p>}

      {groups.length > 1 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm">
          <div className="font-medium text-amber-900">These documents are about {groups.length} different patients</div>
          <p className="mt-0.5 text-xs text-amber-800">
            Only documents about the selected patient fill the form. Matched on last name and date of birth.
          </p>
          <div className="mt-2 space-y-1">
            {groups.map((g) => (
              <label key={g.key} className="flex cursor-pointer items-center gap-2 text-xs text-amber-950">
                <input
                  type="radio"
                  name="patient"
                  checked={primary === g.key}
                  onChange={() => act(() => api.setPrimaryPatient(view.id, g.key))}
                />
                <span className="font-medium">{g.name || "Unnamed"}</span>
                {g.dob && <span className="text-amber-800">DOB {g.dob}</span>}
                <span className="text-amber-700">
                  · {g.doc_ids.length} doc{g.doc_ids.length === 1 ? "" : "s"}
                </span>
              </label>
            ))}
          </div>
        </div>
      )}

      {view.documents.length === 0 && (
        <p className="py-4 text-center text-sm text-slate-500">No documents yet.</p>
      )}

      <ul className="space-y-2">
        {view.documents.map((d) => {
          const ex = d.extraction;
          const s = STATUS[d.status];
          return (
            <li key={d.id} className={`card p-3 ${d.included ? "" : "opacity-60"}`}>
              <div className="flex items-start gap-2">
                <button className="min-w-0 flex-1 text-left" onClick={() => onOpen(d)} title="View document">
                  <div className="truncate text-sm font-medium text-ink hover:underline">{d.filename}</div>
                  <div className="truncate text-xs text-slate-500">
                    {[
                      ex ? DOC_TYPE_LABELS[ex.document_type] : null,
                      ex?.document_date,
                      ex?.patient.full_name?.value,
                      `${d.page_count} page${d.page_count === 1 ? "" : "s"}`,
                    ]
                      .filter(Boolean)
                      .join(" · ")}
                  </div>
                </button>
                <span className={`shrink-0 rounded-full px-2 py-0.5 text-[11px] font-medium ${s.cls}`}>{s.label}</span>
              </div>

              {d.error && <p className="mt-1.5 text-xs text-rose-700">{d.error}</p>}
              {ex?.reading_notes.map((n, i) => (
                <p key={i} className="mt-1.5 text-xs text-amber-800">
                  ⚠ {n}
                </p>
              ))}
              {!d.included && d.status === "extracted" && (
                <p className="mt-1.5 text-xs text-amber-800">Not used: about a different patient.</p>
              )}

              <div className="mt-2 flex flex-wrap gap-1">
                {d.status === "extracted" &&
                  (d.included ? (
                    <button className="btn-ghost text-xs" onClick={() => act(() => api.setInclude(view.id, d.id, false))}>
                      Exclude
                    </button>
                  ) : (
                    <button className="btn-ghost text-xs" onClick={() => act(() => api.setInclude(view.id, d.id, true))}>
                      Use anyway
                    </button>
                  ))}
                {d.include_override !== null && (
                  <button className="btn-ghost text-xs" onClick={() => act(() => api.setInclude(view.id, d.id, null))}>
                    Automatic
                  </button>
                )}
                {d.status === "failed" && (
                  <button className="btn-ghost text-xs" onClick={() => act(() => api.retryDocument(view.id, d.id))}>
                    Retry
                  </button>
                )}
                <button
                  className="btn-ghost text-xs text-rose-700"
                  onClick={() => confirm(`Remove ${d.filename} from this request?`) && act(() => api.deleteDocument(view.id, d.id))}
                >
                  Remove
                </button>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
