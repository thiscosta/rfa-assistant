"use client";

import Link from "next/link";
import { use, useCallback, useEffect, useState } from "react";
import { DocumentsPanel } from "@/components/case/DocumentsPanel";
import { EvidenceViewer } from "@/components/case/EvidenceViewer";
import { ReadinessPanel } from "@/components/case/ReadinessPanel";
import { FormReview } from "@/components/form/FormReview";
import { api, type CaseView, type Evidence, type FormSchema } from "@/lib/api";

type Viewing = { doc_id: string; doc_name: string; quote?: string };

export default function CasePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [view, setView] = useState<CaseView | null>(null);
  const [schema, setSchema] = useState<FormSchema | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [viewing, setViewing] = useState<Viewing | null>(null);

  useEffect(() => {
    Promise.all([api.getCase(id), api.schema()])
      .then(([v, s]) => {
        setView(v);
        setSchema(s);
      })
      .catch((e) => setError(e.message));
  }, [id]);

  const busy =
    !!view && (view.documents.some((d) => d.status === "queued" || d.status === "processing") || view.narrative_status === "drafting");
  useEffect(() => {
    if (!busy) return;
    const t = setInterval(() => api.getCase(id).then(setView).catch(() => {}), 1500);
    return () => clearInterval(t);
  }, [busy, id]);

  const openEvidence = useCallback((e: Evidence) => setViewing(e), []);

  if (error) return <p className="rounded-md bg-rose-50 p-3 text-sm text-rose-700">{error}</p>;
  if (!view || !schema) return <p className="text-sm text-slate-500">Loading…</p>;

  const errors = view.issues.filter((i) => i.severity === "error");
  const viewingDoc = viewing && view.documents.find((d) => d.id === viewing.doc_id);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <Link href="/" className="text-sm text-slate-500 hover:text-ink">
          ← Requests
        </Link>
        <h1 className="text-lg font-semibold text-slate-900">{view.form.fields.member_name?.value || view.label}</h1>
        {busy && <span className="text-xs text-sky-700">Working…</span>}
        <div className="ml-auto flex items-center gap-2">
          <a
            className="btn-primary"
            href={api.pdfUrl(view.id)}
            target="_blank"
            rel="noreferrer"
            onClick={(e) => {
              if (errors.length && !confirm(`${errors.length} required item(s) are still missing or invalid. Open the PDF anyway?`))
                e.preventDefault();
            }}
          >
            Download completed form (PDF)
          </a>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[360px_1fr]">
        <aside className="space-y-4 lg:sticky lg:top-4 lg:max-h-[calc(100vh-2rem)] lg:self-start lg:overflow-y-auto">
          <ReadinessPanel issues={view.issues} schema={schema} />

          <DocumentsPanel
            view={view}
            onChange={setView}
            onOpen={(d) => setViewing({ doc_id: d.id, doc_name: d.filename })}
          />
        </aside>

        <FormReview view={view} schema={schema} onChange={setView} onEvidence={openEvidence} />
      </div>

      {viewing && (
        <EvidenceViewer
          key={`${viewing.doc_id}-${viewing.quote ?? ""}`}
          caseId={view.id}
          evidence={viewing}
          pageCount={viewingDoc?.page_count ?? 1}
          onClose={() => setViewing(null)}
        />
      )}
    </div>
  );
}
