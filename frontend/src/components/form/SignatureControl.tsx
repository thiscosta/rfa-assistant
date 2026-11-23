"use client";

import { api, type CaseView } from "@/lib/api";

export function SignatureControl({ view, onChange }: { view: CaseView; onChange: (fn: () => Promise<CaseView>) => void }) {
  const name = view.form.fields.provider_name?.value;
  if (!name) return <p className="pt-1.5 text-sm text-slate-500">Set the provider name first.</p>;
  return (
    <label className="flex items-start gap-2 pt-1 text-sm text-slate-700">
      <input
        type="checkbox"
        className="mt-1"
        checked={view.typed_signature}
        onChange={(e) => onChange(() => api.setSignature(view.id, e.target.checked))}
      />
      <span>
        I am <strong>{name}</strong>, I reviewed this request, and I apply my typed name as my signature.
        <span className="block text-xs text-slate-500">Leave unchecked to sign the printed form by hand.</span>
      </span>
    </label>
  );
}
