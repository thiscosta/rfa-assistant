from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

DocumentType = Literal[
    "referral_letter",
    "insurance_card",
    "lab_report",
    "intake_form",
    "clinical_note",
    "other",
]


LevelOfCare = Literal[
    "outpatient",
    "inpatient",
    "intensive_outpatient",
    "partial_hospitalization",
    "residential",
    "other",
]


class Quoted(BaseModel):
    value: str = Field(description="Normalized value. Dates as MM/DD/YYYY, phones as (XXX) XXX-XXXX.")
    quote: str = Field(
        description="Verbatim text from the document that supports the value (as written, max ~200 chars)."
    )
    uncertain: bool = Field(
        description="True when the text was hard to read (handwriting, blur) or the value is a guess."
    )


class PatientInfo(BaseModel):
    full_name: Quoted | None
    last_name: str | None
    first_name: str | None
    middle_initial: str | None
    date_of_birth: Quoted | None
    gender: Quoted | None
    phone: Quoted | None
    address: Quoted | None


class InsuranceInfo(BaseModel):
    payer_name: Quoted | None = Field(description="Insurance company, e.g. 'Aetna', 'Anthem Blue Cross Blue Shield'.")
    plan_name: Quoted | None
    member_id: Quoted | None
    group_number: Quoted | None
    payer_phone: Quoted | None = Field(
        description="Prefer a behavioral/mental health or provider services number if listed."
    )
    payer_fax: Quoted | None


class ProviderInfo(BaseModel):
    name: Quoted | None = Field(description="Provider name with credentials, e.g. 'Dr. Susan Okafor, MD'.")
    npi: Quoted | None
    organization: Quoted | None
    phone: Quoted | None
    fax: Quoted | None
    address: Quoted | None
    license_number: Quoted | None


class Diagnosis(BaseModel):
    code: str | None = Field(description="ICD-10-CM code exactly as written, e.g. 'F33.1'. Null if no code is written.")
    description: str
    role: Literal["reason_for_services", "comorbid", "history"] = Field(
        description="reason_for_services: a diagnosis the requested behavioral health services treat. comorbid: other active condition. history: past/resolved."
    )
    quote: str
    uncertain: bool


class Medication(BaseModel):
    name: str = Field(description="As written, e.g. 'Lexapro'.")
    generic_name: str | None = Field(description="Generic name if known, e.g. 'escitalopram'.")
    dose: str | None
    frequency: str | None = Field(description="e.g. 'Daily', 'PRN', 'BID'.")
    prescriber: str | None
    quote: str
    uncertain: bool


class Assessment(BaseModel):
    tool: str = Field(description="Standardized instrument, e.g. 'PHQ-9', 'GAD-7', 'PCL-5', 'AUDIT'.")
    score: str = Field(description="Numeric score, e.g. '14'.")
    interpretation: str | None = Field(description="Severity label if written, e.g. 'moderately severe'.")
    date: str | None = Field(description="MM/DD/YYYY. Use the document date if the score is from that visit.")
    quote: str
    uncertain: bool


class DocumentExtraction(BaseModel):
    document_type: DocumentType
    document_date: str | None = Field(description="Date of the document/visit, MM/DD/YYYY.")
    summary: str = Field(description="One sentence describing the document.")
    patient: PatientInfo
    insurance: InsuranceInfo
    referring_provider: ProviderInfo | None = Field(
        description="Provider who referred the patient (e.g. the PCP on a referral letter)."
    )
    treating_provider: ProviderInfo | None = Field(
        description="Behavioral health provider who wrote this note / will deliver services, if any."
    )
    diagnoses: list[Diagnosis]
    medications: list[Medication]
    assessments: list[Assessment]
    services_requested: list[Quoted] = Field(
        description="Each requested or planned service, e.g. 'Individual psychotherapy (CBT)'."
    )
    requested_frequency: Quoted | None = Field(description="e.g. 'Weekly', '2x/week'.")
    requested_duration: Quoted | None = Field(description="e.g. '12 weeks'.")
    level_of_care: LevelOfCare | None = Field(description="Only if the document indicates it.")
    symptoms: list[Quoted]
    functional_impairment: list[Quoted]
    clinical_history: list[Quoted] = Field(
        description="Prior treatment and response, course of illness, relevant psychiatric/medical/family history."
    )
    risk_factors: list[Quoted] = Field(
        description="Safety-relevant facts (SI/HI, firearms, withdrawal, etc.), including denials such as 'Denies SI/HI'."
    )
    treatment_plan: list[Quoted]
    reading_notes: list[str] = Field(description="Anything illegible or ambiguous a human should double-check.")


DocStatus = Literal["queued", "processing", "extracted", "failed"]


class CaseDocument(BaseModel):
    id: str
    filename: str
    content_type: str
    page_count: int = 0
    status: DocStatus = "queued"
    error: str | None = None
    extraction: DocumentExtraction | None = None

    patient_key: str | None = None
    included: bool = True
    include_override: bool | None = None
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


FieldSource = Literal["document", "inferred", "clinic_profile", "user", "empty"]


class Evidence(BaseModel):
    doc_id: str
    doc_name: str
    quote: str


class Alternative(BaseModel):
    value: str
    evidence: Evidence


class FieldState(BaseModel):
    value: str = ""
    source: FieldSource = "empty"
    evidence: list[Evidence] = Field(default_factory=list)
    note: str | None = None
    uncertain: bool = False
    alternatives: list[Alternative] = Field(default_factory=list)


class TableRow(BaseModel):
    cells: dict[str, str]
    source: FieldSource = "document"
    evidence: list[Evidence] = Field(default_factory=list)
    uncertain: bool = False


class Issue(BaseModel):
    field: str | None
    severity: Literal["error", "warning"]
    message: str


class RfaForm(BaseModel):
    fields: dict[str, FieldState] = Field(default_factory=dict)
    medications: list[TableRow] = Field(default_factory=list)
    assessments: list[TableRow] = Field(default_factory=list)
    medications_edited: bool = False
    assessments_edited: bool = False


class Case(BaseModel):
    id: str
    label: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    documents: list[CaseDocument] = Field(default_factory=list)
    primary_patient_key: str | None = None
    form: RfaForm = Field(default_factory=RfaForm)
    narrative_status: Literal["idle", "drafting", "done", "failed"] = "idle"
    narrative_error: str | None = None
    narrative_draft: NarrativeDraft | None = None
    narrative_facts_hash: str | None = None
    typed_signature: bool = False

    def document(self, doc_id: str) -> CaseDocument:
        for d in self.documents:
            if d.id == doc_id:
                return d
        raise KeyError(doc_id)


class ClinicProvider(BaseModel):
    name: str
    npi: str = ""
    license_number: str = ""


class ClinicProfile(BaseModel):
    facility_name: str = ""
    tax_id: str = ""
    phone: str = ""
    fax: str = ""
    address: str = ""
    providers: list[ClinicProvider] = Field(default_factory=list)
    default_provider_index: int | None = None


class NarrativeDraft(BaseModel):
    presenting_symptoms: str = Field(
        description="Presenting symptoms and functional impairment. At most 340 characters (4 lines on the form)."
    )
    clinical_history: str = Field(
        description="Prior treatments, medications, response. At most 330 characters (4 lines on the form)."
    )
    treatment_goals: list[str] = Field(
        description="Up to 3 measurable goals, no numbering. The first under 65 characters, the others under 100."
    )
    medical_necessity: str = Field(
        description="Why this level of care is medically necessary. At most 440 characters (5 lines on the form)."
    )
    risk_without_services: str = Field(
        description="Risk if services are not provided. At most 230 characters (3 lines on the form)."
    )
    unsupported_gaps: list[str] = Field(description="Things a reviewer would expect that the documents do not say.")


Case.model_rebuild()
