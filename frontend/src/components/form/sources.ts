import type { Evidence, FieldState } from "@/lib/api";

export type OpenEvidence = (e: Evidence) => void;

export const SOURCE: Record<FieldState["source"], { label: string; cls: string; title: string }> = {
  document: { label: "From documents", cls: "bg-emerald-50 text-emerald-700", title: "Copied from an uploaded document" },
  inferred: { label: "Suggested: check", cls: "bg-amber-50 text-amber-800", title: "Worked out by the app, not written in a document" },
  clinic_profile: { label: "Clinic settings", cls: "bg-sky-50 text-sky-700", title: "From Clinic settings" },
  user: { label: "Edited", cls: "bg-violet-50 text-violet-700", title: "Typed by a reviewer; the app won't overwrite it" },
  empty: { label: "Empty", cls: "bg-slate-100 text-slate-500", title: "" },
};
