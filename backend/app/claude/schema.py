from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from app.domain.models import (
    Assessment,
    Diagnosis,
    DocumentExtraction,
    InsuranceInfo,
    Medication,
    PatientInfo,
    ProviderInfo,
    Quoted,
)

# Flat on purpose: the nested, nullable DocumentExtraction compiled to a structured-output grammar
# the API rejects as too large. to_extraction() rebuilds the internal model.
FactField = Literal[
    "patient_full_name",
    "patient_last_name",
    "patient_first_name",
    "patient_middle_initial",
    "patient_dob",
    "patient_gender",
    "patient_phone",
    "patient_address",
    "payer_name",
    "plan_name",
    "member_id",
    "group_number",
    "payer_phone",
    "payer_fax",
    "referring_name",
    "referring_npi",
    "referring_organization",
    "referring_phone",
    "referring_fax",
    "referring_address",
    "treating_name",
    "treating_npi",
    "treating_organization",
    "treating_phone",
    "treating_fax",
    "treating_address",
    "treating_license",
    "requested_frequency",
    "requested_duration",
    "service_requested",
    "symptom",
    "functional_impairment",
    "clinical_history",
    "risk_factor",
    "treatment_plan",
]


FIELD_GUIDE = """Fact fields (use each single-value field at most once; the last six may repeat):
- patient_*: the patient's identity and contact details. patient_dob is the date of birth.
- payer_name: the insurance company. plan_name, member_id, group_number as printed. payer_phone: prefer a \
behavioral or mental health number if listed. payer_fax: only if printed.
- referring_*: the provider who referred the patient (e.g. the PCP who wrote a referral letter).
- treating_*: the behavioral health provider who wrote this note or will deliver the services \
(treating_license: license number).
- requested_frequency (e.g. "Weekly", "2x/week") and requested_duration (e.g. "12 weeks") of the requested services.
- service_requested: one entry per requested or planned service (e.g. "Individual psychotherapy (CBT)").
- symptom, functional_impairment, clinical_history (prior treatment and response, course of illness, \
relevant psychiatric/medical/family history), risk_factor (SI/HI, firearms, withdrawal..., including \
denials such as "Denies SI/HI"), treatment_plan: one entry per distinct point."""


class Fact(BaseModel):
    field: FactField
    value: str
    quote: str
    uncertain: bool


class FlatDiagnosis(BaseModel):
    code: str
    description: str
    role: Literal["reason_for_services", "comorbid", "history"]
    quote: str
    uncertain: bool


class FlatMedication(BaseModel):
    name: str
    generic_name: str
    dose: str
    frequency: str
    prescriber: str
    quote: str
    uncertain: bool


class FlatAssessment(BaseModel):
    tool: str
    score: str
    interpretation: str
    date: str
    quote: str
    uncertain: bool


class ClaudeExtraction(BaseModel):
    document_type: Literal["referral_letter", "insurance_card", "lab_report", "intake_form", "clinical_note", "other"]
    document_date: str
    summary: str
    level_of_care: Literal[
        "not_stated",
        "outpatient",
        "inpatient",
        "intensive_outpatient",
        "partial_hospitalization",
        "residential",
        "other",
    ]
    facts: list[Fact]
    diagnoses: list[FlatDiagnosis]
    medications: list[FlatMedication]
    assessments: list[FlatAssessment]
    reading_notes: list[str]


def _o(s: str) -> str | None:
    s = s.strip()
    return s or None


def to_extraction(flat: ClaudeExtraction) -> DocumentExtraction:
    single: dict[str, Quoted] = {}
    multi: dict[str, list[Quoted]] = {}
    for f in flat.facts:
        if not f.value.strip():
            continue
        q = Quoted(value=f.value.strip(), quote=f.quote, uncertain=f.uncertain)
        if f.field in (
            "service_requested",
            "symptom",
            "functional_impairment",
            "clinical_history",
            "risk_factor",
            "treatment_plan",
        ):
            multi.setdefault(f.field, []).append(q)
        else:
            single.setdefault(f.field, q)

    def provider(prefix: str) -> ProviderInfo | None:
        p = ProviderInfo(
            name=single.get(f"{prefix}_name"),
            npi=single.get(f"{prefix}_npi"),
            organization=single.get(f"{prefix}_organization"),
            phone=single.get(f"{prefix}_phone"),
            fax=single.get(f"{prefix}_fax"),
            address=single.get(f"{prefix}_address"),
            license_number=single.get(f"{prefix}_license"),
        )
        return p if any(getattr(p, k) for k in p.model_fields) else None

    v = lambda k: single[k].value if k in single else None  # noqa: E731
    return DocumentExtraction(
        document_type=flat.document_type,
        document_date=_o(flat.document_date),
        summary=flat.summary,
        patient=PatientInfo(
            full_name=single.get("patient_full_name"),
            last_name=v("patient_last_name"),
            first_name=v("patient_first_name"),
            middle_initial=v("patient_middle_initial"),
            date_of_birth=single.get("patient_dob"),
            gender=single.get("patient_gender"),
            phone=single.get("patient_phone"),
            address=single.get("patient_address"),
        ),
        insurance=InsuranceInfo(
            payer_name=single.get("payer_name"),
            plan_name=single.get("plan_name"),
            member_id=single.get("member_id"),
            group_number=single.get("group_number"),
            payer_phone=single.get("payer_phone"),
            payer_fax=single.get("payer_fax"),
        ),
        referring_provider=provider("referring"),
        treating_provider=provider("treating"),
        diagnoses=[
            Diagnosis(code=_o(d.code), description=d.description, role=d.role, quote=d.quote, uncertain=d.uncertain)
            for d in flat.diagnoses
        ],
        medications=[
            Medication(
                name=m.name,
                generic_name=_o(m.generic_name),
                dose=_o(m.dose),
                frequency=_o(m.frequency),
                prescriber=_o(m.prescriber),
                quote=m.quote,
                uncertain=m.uncertain,
            )
            for m in flat.medications
        ],
        assessments=[
            Assessment(
                tool=a.tool,
                score=a.score,
                interpretation=_o(a.interpretation),
                date=_o(a.date),
                quote=a.quote,
                uncertain=a.uncertain,
            )
            for a in flat.assessments
        ],
        services_requested=multi.get("service_requested", []),
        requested_frequency=single.get("requested_frequency"),
        requested_duration=single.get("requested_duration"),
        level_of_care=None if flat.level_of_care == "not_stated" else flat.level_of_care,
        symptoms=multi.get("symptom", []),
        functional_impairment=multi.get("functional_impairment", []),
        clinical_history=multi.get("clinical_history", []),
        risk_factors=multi.get("risk_factor", []),
        treatment_plan=multi.get("treatment_plan", []),
        reading_notes=flat.reading_notes,
    )
