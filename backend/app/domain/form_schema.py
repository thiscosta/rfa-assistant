from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

Kind = Literal["text", "date", "longtext", "choice"]


@dataclass(frozen=True)
class FormField:
    key: str
    section: str
    label: str
    kind: Kind = "text"
    required: bool = False
    occurrence: int = 0
    page: int = 0
    lines: int = 1
    help: str | None = None
    choices: tuple[str, ...] = ()


SERVICE_TYPES = (
    "Outpatient",
    "Inpatient",
    "Intensive Outpatient",
    "Partial Hospitalization",
    "Residential",
    "Other",
)


SECTIONS = {
    "header": "Payer",
    "A": "Section A: Member information",
    "B": "Section B: Requesting provider",
    "C": "Section C: Referring provider (if different)",
    "D": "Section D: Service information",
    "E": "Section E: Clinical information",
    "F": "Section F: Clinical justification",
    "G": "Section G: Attestation",
}


FIELDS: list[FormField] = [
    FormField("payer", "header", "Payer:", required=True),
    FormField("request_date", "header", "Date of Request:", "date", required=True),
    FormField(
        "payer_fax",
        "header",
        "Payer Fax:",
        help="Usually on the payer's prior-authorization fax sheet, not on the member card.",
    ),
    FormField("payer_phone", "header", "Payer Phone:"),
    FormField("member_name", "A", "Member Name (Last, First, MI):", required=True),
    FormField("member_dob", "A", "Date of Birth:", "date", required=True),
    FormField("member_gender", "A", "Gender:"),
    FormField("member_id", "A", "Member ID:", required=True),
    FormField("group_number", "A", "Group Number:"),
    FormField("member_phone", "A", "Phone Number:"),
    FormField("member_address", "A", "Address:", occurrence=0),
    FormField("provider_name", "B", "Provider Name:", required=True),
    FormField("provider_npi", "B", "Provider NPI:", required=True),
    FormField("facility_name", "B", "Facility/Practice Name:", required=True),
    FormField("tax_id", "B", "Tax ID:", required=True),
    FormField("provider_phone", "B", "Phone:", occurrence=0, required=True),
    FormField("provider_fax", "B", "Fax:", occurrence=0),
    FormField("provider_address", "B", "Address:", occurrence=1, required=True),
    FormField("referring_name", "C", "Referring Provider Name:"),
    FormField("referring_npi", "C", "Referring Provider NPI:"),
    FormField("referring_phone", "C", "Phone:", occurrence=1),
    FormField("service_type", "D", "Type of Service Requested:", "choice", required=True, choices=SERVICE_TYPES),
    FormField("service_setting", "D", "Service Setting:"),
    FormField("cpt_codes", "D", "CPT/HCPCS Code(s):", required=True, help="Comma-separated."),
    FormField("icd10_codes", "D", "ICD-10 Diagnosis Code(s):", required=True, help="Comma-separated, primary first."),
    FormField("diagnosis_descriptions", "D", "Diagnosis Description(s):", required=True),
    FormField("start_date", "D", "Requested Start Date:", "date", required=True),
    FormField("end_date", "D", "Requested End Date:", "date", required=True),
    FormField("sessions_units", "D", "Number of Sessions/Units:", required=True),
    FormField("frequency", "D", "Frequency:", required=True),
    FormField(
        "presenting_symptoms",
        "E",
        "Presenting symptoms and functional impairment:",
        "longtext",
        required=True,
        page=1,
        lines=4,
    ),
    FormField(
        "clinical_history",
        "E",
        "Relevant clinical history (prior treatments, medications, response):",
        "longtext",
        page=1,
        lines=4,
    ),
    FormField(
        "treatment_goals",
        "E",
        "Treatment goals and expected outcomes:",
        "longtext",
        required=True,
        page=1,
        lines=3,
        help="One goal per line.",
    ),
    FormField(
        "medical_necessity",
        "F",
        "Why is this level of care/service medically necessary?",
        "longtext",
        required=True,
        page=1,
        lines=5,
    ),
    FormField(
        "risk_without_services",
        "F",
        "What is the risk if services are not provided?",
        "longtext",
        required=True,
        page=1,
        lines=3,
    ),
    FormField(
        "signature",
        "G",
        "Provider Signature:",
        page=1,
        help="Filled only when the provider chooses to sign with their typed name.",
    ),
    FormField("printed_name", "G", "Printed Name:", required=True, page=1),
    FormField("signature_date", "G", "Date:", "date", required=True, page=1, occurrence=0),
    FormField("license_number", "G", "License #:", required=True, page=1),
]


FIELDS_BY_KEY = {f.key: f for f in FIELDS}


MEDICATION_COLUMNS = ("medication", "dose", "frequency", "prescriber")


ASSESSMENT_COLUMNS = ("tool", "score", "date")


MEDICATION_ROWS_ON_FORM = 3


ASSESSMENT_ROWS_ON_FORM = 2


def schema_payload() -> dict:
    return {
        "sections": SECTIONS,
        "fields": [asdict(f) for f in FIELDS],
        "medication_columns": MEDICATION_COLUMNS,
        "assessment_columns": ASSESSMENT_COLUMNS,
        "medication_rows_on_form": MEDICATION_ROWS_ON_FORM,
        "assessment_rows_on_form": ASSESSMENT_ROWS_ON_FORM,
    }
