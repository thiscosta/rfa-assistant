"use client";

import { useEffect, useRef, useState } from "react";
import type { Issue, TableRow } from "@/lib/api";
import { SOURCE, type OpenEvidence } from "./sources";

export function TableEditor({
  title,
  columns,
  rowsOnForm,
  rows,
  edited,
  issues,
  onSave,
  onReset,
  onEvidence,
}: {
  title: string;
  columns: string[];
  rowsOnForm: number;
  rows: TableRow[];
  edited: boolean;
  issues: Issue[];
  onSave: (rows: Record<string, string>[]) => void;
  onReset: () => void;
  onEvidence: OpenEvidence;
}) {
  const [draft, setDraft] = useState(rows.map((r) => r.cells));
  const dirty = useRef(false);
  useEffect(() => {
    if (!dirty.current) setDraft(rows.map((r) => r.cells));
  }, [rows]);

  const commit = (next = draft) => {
    dirty.current = false;
    onSave(next.filter((r) => Object.values(r).some((v) => v.trim())));
  };

  return (
    <div className="px-4 py-3">
      <div className="mb-2 flex items-center gap-2">
        <h3 className="text-sm font-medium text-slate-700">{title}</h3>
        <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${edited ? SOURCE.user.cls : SOURCE.document.cls}`}>
          {edited ? "Edited" : rows.length ? "From documents" : "Empty"}
        </span>
        {rows.length > rowsOnForm && (
          <span className="text-xs text-slate-500">
            The form has {rowsOnForm} rows; the rest go on an addendum page.
          </span>
        )}
        {edited && (
          <button className="ml-auto text-xs text-slate-500 underline" onClick={onReset}>
            Undo edits (fill automatically)
          </button>
        )}
      </div>
      {issues.map((i, n) => (
        <p key={n} className="mb-1 text-xs text-amber-800">
          {i.message}
        </p>
      ))}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
              {columns.map((c) => (
                <th key={c} className="px-2 py-1.5 font-medium">
                  {c}
                </th>
              ))}
              <th className="w-24" />
            </tr>
          </thead>
          <tbody>
            {draft.map((row, i) => (
              <tr key={i} className="border-t border-slate-100">
                {columns.map((c) => (
                  <td key={c} className="p-1">
                    <input
                      className={`input py-1 ${rows[i]?.uncertain ? "border-amber-400" : ""}`}
                      value={row[c] ?? ""}
                      onChange={(e) => {
                        dirty.current = true;
                        setDraft(draft.map((r, j) => (j === i ? { ...r, [c]: e.target.value } : r)));
                      }}
                      onBlur={() => dirty.current && commit()}
                    />
                  </td>
                ))}
                <td className="whitespace-nowrap px-1 text-right">
                  {rows[i]?.evidence[0] && (
                    <button className="text-xs text-ink hover:underline" title={rows[i].evidence[0].quote} onClick={() => onEvidence(rows[i].evidence[0])}>
                      ↗ source
                    </button>
                  )}
                  <button
                    className="ml-2 text-xs text-slate-400 hover:text-rose-700"
                    aria-label="Remove row"
                    onClick={() => {
                      const next = draft.filter((_, j) => j !== i);
                      setDraft(next);
                      commit(next);
                    }}
                  >
                    ✕
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <button
        className="btn-ghost mt-1 text-xs"
        onClick={() => {
          dirty.current = true;
          setDraft([...draft, Object.fromEntries(columns.map((c) => [c, ""]))]);
        }}
      >
        + Add row
      </button>
    </div>
  );
}
