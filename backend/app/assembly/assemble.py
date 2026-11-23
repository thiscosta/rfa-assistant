from __future__ import annotations

from datetime import date, timedelta

from app.assembly.clinical import (
    NARRATIVE_FIELDS,
    assessment_rows,
    diagnosis_codes,
    facts_hash,
    latest_per_tool,
    medication_rows,
    narrative_facts,
)
from app.assembly.identity import resolve_identity
from app.assembly.providers import best_provider, match_clinic_provider, provider_field, same_provider
from app.assembly.services import (
    LEVEL_LABELS,
    SETTINGS,
    START_OFFSET_DAYS,
    frequency_field,
    requested_service_texts,
    suggest_cpt,
)
from app.assembly.sources import (
    Candidate,
    candidates_for,
    evidence_from,
    field_from_candidates,
    inferred_field,
    profile_field,
    ranked_documents,
)
from app.domain.form_schema import FIELDS
from app.domain.models import Case, ClinicProfile, FieldState, RfaForm
from app.domain.normalize import fmt_date, member_name_last_first, normalize_date, normalize_phone


def assemble(case: Case, profile: ClinicProfile, today: date | None = None) -> tuple[RfaForm, dict]:
    today = today or date.today()
    resolve_identity(case)
    prev = case.form
    f: dict[str, FieldState] = {}

    f["payer"] = field_from_candidates(candidates_for(case, "insurance", lambda e: e.insurance.payer_name))
    f["payer_phone"] = field_from_candidates(
        candidates_for(case, "insurance", lambda e: e.insurance.payer_phone, normalize_phone)
    )
    f["payer_fax"] = field_from_candidates(
        candidates_for(case, "insurance", lambda e: e.insurance.payer_fax, normalize_phone)
    )
    if not f["payer_fax"].value:
        f["payer_fax"].note = "Not on the member's documents; use the payer's prior-authorization fax number."
    f["request_date"] = inferred_field(fmt_date(today), "Today's date.")

    f["member_name"] = _member_name(case)
    f["member_dob"] = field_from_candidates(
        candidates_for(case, "demographics", lambda e: e.patient.date_of_birth, normalize_date)
    )
    f["member_gender"] = field_from_candidates(
        candidates_for(case, "demographics", lambda e: e.patient.gender, lambda v: v.strip().capitalize())
    )
    f["member_id"] = field_from_candidates(candidates_for(case, "insurance", lambda e: e.insurance.member_id))
    f["group_number"] = field_from_candidates(candidates_for(case, "insurance", lambda e: e.insurance.group_number))
    f["member_phone"] = field_from_candidates(
        candidates_for(case, "demographics", lambda e: e.patient.phone, normalize_phone)
    )
    f["member_address"] = field_from_candidates(candidates_for(case, "demographics", lambda e: e.patient.address))

    treating_doc, treating = best_provider(case, "clinical", lambda e: e.treating_provider)
    clinic_provider = match_clinic_provider(profile, treating)
    if clinic_provider:
        f["provider_name"] = profile_field(clinic_provider.name)
        f["provider_npi"] = profile_field(clinic_provider.npi)
        f["license_number"] = profile_field(clinic_provider.license_number)
    else:
        f["provider_name"] = provider_field(treating_doc, treating, "name")
        f["provider_npi"] = provider_field(treating_doc, treating, "npi")
        f["license_number"] = provider_field(treating_doc, treating, "license_number")
        if not f["provider_name"].value:
            f["provider_name"].note = "Add the treating provider under Clinic settings, or type it here."
    f["facility_name"] = (
        profile_field(profile.facility_name)
        if profile.facility_name
        else provider_field(treating_doc, treating, "organization")
    )
    f["tax_id"] = profile_field(profile.tax_id)
    if not f["tax_id"].value:
        f["tax_id"].note = "The clinic's Tax ID is not in patient documents; set it once under Clinic settings."
    f["provider_phone"] = (
        profile_field(normalize_phone(profile.phone))
        if profile.phone
        else provider_field(treating_doc, treating, "phone")
    )
    f["provider_fax"] = (
        profile_field(normalize_phone(profile.fax)) if profile.fax else provider_field(treating_doc, treating, "fax")
    )
    f["provider_address"] = (
        profile_field(profile.address) if profile.address else provider_field(treating_doc, treating, "address")
    )

    ref_doc, referring = best_provider(case, "referral", lambda e: e.referring_provider)
    if referring and same_provider(referring, f["provider_name"].value, f["provider_npi"].value):
        referring, ref_doc = None, None
    f["referring_name"] = provider_field(ref_doc, referring, "name")
    f["referring_npi"] = provider_field(ref_doc, referring, "npi")
    f["referring_phone"] = provider_field(ref_doc, referring, "phone", normalize_phone)

    dx_codes, dx_descs, dx_evidence = diagnosis_codes(case)
    f["icd10_codes"] = (
        FieldState(value=", ".join(dx_codes), source="document", evidence=dx_evidence) if dx_codes else FieldState()
    )
    f["diagnosis_descriptions"] = (
        FieldState(value="; ".join(dx_descs), source="document", evidence=dx_evidence) if dx_descs else FieldState()
    )
    if dx_codes and any(not c for c in dx_codes):
        f["icd10_codes"].note = "A diagnosis has no ICD-10 code in the documents."

    service_texts, service_evidence = requested_service_texts(case)
    level = next(
        (
            (d, d.extraction.level_of_care)
            for d in ranked_documents(case, "clinical")
            if d.extraction and d.extraction.level_of_care
        ),
        None,
    )
    if level:
        f["service_type"] = FieldState(
            value=LEVEL_LABELS[level[1]],
            source="document",
            evidence=[evidence_from(level[0], level[0].extraction.summary)],
        )  # type: ignore[union-attr]
    elif service_texts or dx_codes:
        f["service_type"] = inferred_field(
            "Outpatient", "No level of care stated; requested services read as outpatient.", service_evidence
        )
    else:
        f["service_type"] = FieldState()
    stype = f["service_type"].value
    f["service_setting"] = inferred_field(SETTINGS.get(stype, ""), "Follows from the type of service.")

    freq_state, per_week, weeks, freq_evidence = frequency_field(case, service_texts, service_evidence)
    f["frequency"] = freq_state
    start = today + timedelta(days=START_OFFSET_DAYS)
    end = start + timedelta(weeks=weeks) - timedelta(days=1)
    f["start_date"] = inferred_field(
        fmt_date(start), f"Request date + {START_OFFSET_DAYS} days, to allow for payer review."
    )
    f["end_date"] = inferred_field(fmt_date(end), f"Start date + {weeks} weeks.", freq_evidence)
    if per_week:
        f["sessions_units"] = inferred_field(
            str(round(per_week * weeks)),
            f"{f['frequency'].value} for {weeks} weeks (psychotherapy sessions). Adjust if evaluation or medication visits are billed separately.",
            freq_evidence,
        )
    else:
        f["sessions_units"] = FieldState(note="No frequency in the documents.")

    cpts = suggest_cpt(service_texts, stype)
    f["cpt_codes"] = inferred_field(
        ", ".join(c for c, _ in cpts),
        "Suggested from the requested services ("
        + "; ".join(f"{c}: {label}" for c, label in cpts)
        + "). Confirm against the payer's fee schedule."
        if cpts
        else "No requested services found to suggest codes from.",
        service_evidence,
    )

    medications = medication_rows(case)
    assessments_all = assessment_rows(case)
    latest = latest_per_tool(assessments_all)

    facts = narrative_facts(case, f, medications, assessments_all)
    draft = case.narrative_draft if case.narrative_draft and case.narrative_facts_hash == facts_hash(facts) else None
    if draft:
        note = "Drafted by Claude from the documents. Review before signing."
        f["presenting_symptoms"] = inferred_field(draft.presenting_symptoms, note)
        f["clinical_history"] = inferred_field(draft.clinical_history, note)
        f["treatment_goals"] = inferred_field("\n".join(draft.treatment_goals[:3]), note)
        f["medical_necessity"] = inferred_field(draft.medical_necessity, note)
        f["risk_without_services"] = inferred_field(draft.risk_without_services, note)
    else:
        for key in NARRATIVE_FIELDS:
            f[key] = FieldState(note="Claude drafts this once all documents are read.")

    f["printed_name"] = f["provider_name"].model_copy()
    f["signature"] = (
        FieldState(value=f["provider_name"].value, source="user", note="Typed signature applied by the provider.")
        if case.typed_signature and f["provider_name"].value
        else FieldState(note="Signed by the provider: by hand on the printed form, or by applying a typed signature.")
    )
    f["signature_date"] = inferred_field(fmt_date(today), "Today's date.")

    # Reviewer edits always win over re-extracted values.
    for key, old in prev.fields.items():
        if old.source == "user" and key != "signature":
            f[key] = old
    for field in FIELDS:
        f.setdefault(field.key, FieldState())

    form = RfaForm(
        fields=f,
        medications=prev.medications if prev.medications_edited else medications,
        assessments=prev.assessments if prev.assessments_edited else latest,
        medications_edited=prev.medications_edited,
        assessments_edited=prev.assessments_edited,
    )
    return form, facts


def _member_name(case: Case) -> FieldState:
    cands = []
    for doc in ranked_documents(case, "demographics"):
        p = doc.extraction.patient  # type: ignore[union-attr]
        if not (p.full_name or (p.first_name and p.last_name)):
            continue
        full = p.full_name.value if p.full_name else None
        value = member_name_last_first(p.first_name, p.middle_initial, p.last_name, full)
        cands.append(
            Candidate(
                value,
                evidence_from(doc, p.full_name.quote if p.full_name else value),
                bool(p.full_name and p.full_name.uncertain),
            )
        )
    return field_from_candidates(cands)
