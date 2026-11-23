"use client";

import { useState } from "react";
import { api, type CaseView, type FormSchema } from "@/lib/api";
import { FieldRow } from "./FieldRow";
import { NarrativeBanner } from "./NarrativeBanner";
import type { OpenEvidence } from "./sources";
import { TableEditor } from "./TableEditor";

export function FormReview({
  view,
  schema,
  onChange,
  onEvidence,
}: {
  view: CaseView;
  schema: FormSchema;
  onChange: (v: CaseView) => void;
  onEvidence: OpenEvidence;
}) {
  const [error, setError] = useState<string | null>(null);
  const save = async (fn: () => Promise<CaseView>) => {
    try {
      setError(null);
      onChange(await fn());
    } catch (e) {
      setError((e as Error).message);
    }
  };
  const issuesFor = (key: string) => view.issues.filter((i) => i.field === key);

  return (
    <div className="space-y-5">
      {error && <p className="rounded-md bg-rose-50 p-3 text-sm text-rose-700">{error}</p>}
      {Object.entries(schema.sections).map(([section, title]) => (
        <section key={section} id={`section-${section}`} className="card overflow-hidden">
          <h2 className="bg-ink px-4 py-2 text-sm font-semibold uppercase tracking-wide text-white">{title}</h2>
          {section === "E" && <NarrativeBanner view={view} onChange={onChange} />}
          <div className="divide-y divide-slate-100">
            {schema.fields
              .filter((f) => f.section === section)
              .map((def) => (
                <div key={def.key}>
                  <FieldRow
                    def={def}
                    state={view.form.fields[def.key]}
                    issues={issuesFor(def.key)}
                    onSave={(value) => save(() => api.patchFields(view.id, { [def.key]: value }))}
                    onReset={() => save(() => api.patchFields(view.id, {}, [def.key]))}
                    onEvidence={onEvidence}
                    signature={def.key === "signature" ? { view, onChange: save } : undefined}
                  />
                  {def.key === "clinical_history" && (
                    <>
                      <TableEditor
                        title="Current medications"
                        columns={schema.medication_columns}
                        rowsOnForm={schema.medication_rows_on_form}
                        rows={view.form.medications}
                        edited={view.form.medications_edited}
                        issues={issuesFor("medications")}
                        onSave={(rows) => save(() => api.putTable(view.id, "medications", rows))}
                        onReset={() => save(() => api.resetTable(view.id, "medications"))}
                        onEvidence={onEvidence}
                      />
                      <TableEditor
                        title="Most recent validated assessment scores"
                        columns={schema.assessment_columns}
                        rowsOnForm={schema.assessment_rows_on_form}
                        rows={view.form.assessments}
                        edited={view.form.assessments_edited}
                        issues={issuesFor("assessments")}
                        onSave={(rows) => save(() => api.putTable(view.id, "assessments", rows))}
                        onReset={() => save(() => api.resetTable(view.id, "assessments"))}
                        onEvidence={onEvidence}
                      />
                    </>
                  )}
                </div>
              ))}
          </div>
        </section>
      ))}
    </div>
  );
}
