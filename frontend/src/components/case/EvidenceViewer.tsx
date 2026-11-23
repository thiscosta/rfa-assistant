"use client";

import { useEffect, useState } from "react";
import { api, type Evidence } from "@/lib/api";

export function EvidenceViewer({
  caseId,
  evidence,
  pageCount,
  onClose,
}: {
  caseId: string;
  evidence: Evidence | { doc_id: string; doc_name: string; quote?: string };
  pageCount: number;
  onClose: () => void;
}) {
  const [page, setPage] = useState(0);
  const [shown, setShown] = useState<number | null>(null);
  const [src, setSrc] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  const quote = "quote" in evidence ? evidence.quote : undefined;

  useEffect(() => {
    let revoked: string | null = null;
    const url = api.previewUrl(caseId, evidence.doc_id, page, shown === null ? quote : undefined);
    fetch(url)
      .then(async (res) => {
        if (!res.ok) throw new Error();
        const p = Number(res.headers.get("X-Page") ?? page);
        const blob = await res.blob();
        revoked = URL.createObjectURL(blob);
        setSrc(revoked);
        setShown(p);
        if (p !== page) setPage(p);
      })
      .catch(() => setFailed(true));
    return () => {
      if (revoked) URL.revokeObjectURL(revoked);
    };
  }, [caseId, evidence.doc_id, page]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4" onClick={onClose}>
      <div
        className="flex max-h-full w-full max-w-3xl flex-col overflow-hidden rounded-lg bg-white shadow-xl"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-label={`Source: ${evidence.doc_name}`}
      >
        <div className="flex items-center gap-3 border-b border-slate-200 px-4 py-2.5">
          <div className="min-w-0 flex-1">
            <div className="truncate text-sm font-medium text-slate-900">{evidence.doc_name}</div>
            <div className="text-xs text-slate-500">
              Page {page + 1} of {pageCount || "?"}
            </div>
          </div>
          <button className="btn-ghost text-xs" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
            ← Prev
          </button>
          <button className="btn-ghost text-xs" disabled={page >= pageCount - 1} onClick={() => setPage((p) => p + 1)}>
            Next →
          </button>
          <a className="btn-ghost text-xs" href={api.fileUrl(caseId, evidence.doc_id)} target="_blank" rel="noreferrer">
            Open file
          </a>
          <button className="btn-secondary text-xs" onClick={onClose}>
            Close
          </button>
        </div>
        {quote && (
          <div className="border-b border-amber-100 bg-amber-50 px-4 py-2 text-sm text-amber-900">
            <span className="text-xs font-medium uppercase tracking-wide text-amber-700">Supporting text</span>
            <p className="font-mono text-[13px]">“{quote}”</p>
          </div>
        )}
        <div className="overflow-auto bg-slate-100 p-3">
          {failed ? (
            <p className="p-6 text-center text-sm text-slate-500">Couldn&apos;t render this page.</p>
          ) : src ? (
            <img src={src} alt={`${evidence.doc_name}, page ${page + 1}`} className="mx-auto max-w-full bg-white shadow" />
          ) : (
            <p className="p-6 text-center text-sm text-slate-500">Loading page…</p>
          )}
        </div>
      </div>
    </div>
  );
}
