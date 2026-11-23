export type FieldSource = "document" | "inferred" | "clinic_profile" | "user" | "empty";

export interface Evidence {
  doc_id: string;
  doc_name: string;
  quote: string;
}

export interface FieldState {
  value: string;
  source: FieldSource;
  evidence: Evidence[];
  note: string | null;
  uncertain: boolean;
  alternatives: { value: string; evidence: Evidence }[];
}

export interface TableRow {
  cells: Record<string, string>;
  source: FieldSource;
  evidence: Evidence[];
  uncertain: boolean;
}

export interface Quoted {
  value: string;
  quote: string;
  uncertain: boolean;
}

export interface Extraction {
  document_type: string;
  document_date: string | null;
  summary: string;
  patient: { full_name: Quoted | null; date_of_birth: Quoted | null };
  reading_notes: string[];
}

export interface CaseDocument {
  id: string;
  filename: string;
  content_type: string;
  page_count: number;
  status: "queued" | "processing" | "extracted" | "failed";
  error: string | null;
  extraction: Extraction | null;
  patient_key: string | null;
  included: boolean;
  include_override: boolean | null;
}

export interface Issue {
  field: string | null;
  severity: "error" | "warning";
  message: string;
}

export interface PatientGroup {
  key: string;
  name: string;
  dob: string;
  doc_ids: string[];
}

export interface CaseView {
  id: string;
  label: string;
  documents: CaseDocument[];
  primary_patient_key: string | null;
  form: {
    fields: Record<string, FieldState>;
    medications: TableRow[];
    assessments: TableRow[];
    medications_edited: boolean;
    assessments_edited: boolean;
  };
  narrative_status: "idle" | "drafting" | "done" | "failed";
  narrative_error: string | null;
  narrative_draft: { unsupported_gaps: string[] } | null;
  typed_signature: boolean;
  issues: Issue[];
  patient_groups: PatientGroup[];
}

export interface CaseSummary {
  id: string;
  label: string;
  member_name: string;
  payer: string;
  documents: number;
  errors: number;
  updated_at: string;
}

export interface FormFieldDef {
  key: string;
  section: string;
  label: string;
  kind: "text" | "date" | "longtext" | "choice";
  required: boolean;
  lines: number;
  help: string | null;
  choices: string[];
}

export interface FormSchema {
  sections: Record<string, string>;
  fields: FormFieldDef[];
  medication_columns: string[];
  assessment_columns: string[];
  medication_rows_on_form: number;
  assessment_rows_on_form: number;
}

export interface ClinicProvider {
  name: string;
  npi: string;
  license_number: string;
}

export interface ClinicProfile {
  facility_name: string;
  tax_id: string;
  phone: string;
  fax: string;
  address: string;
  providers: ClinicProvider[];
  default_provider_index: number | null;
}
