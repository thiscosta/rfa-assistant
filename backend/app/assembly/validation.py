from __future__ import annotations

import re
from datetime import date

from app.domain.form_schema import FIELDS, SERVICE_TYPES
from app.domain.models import Case, Issue
from app.domain.normalize import CPT_RE, ICD10_RE, digits, npi_is_valid, parse_date


def validate(case: Case) -> list[Issue]:
    f = case.form.fields
    issues: list[Issue] = []

    def val(key: str) -> str:
        return f[key].value.strip() if key in f else ""

    for field in FIELDS:
        if field.required and not val(field.key):
            issues.append(Issue(field=field.key, severity="error", message=f"{field.label.rstrip(':?')} is required."))

    for key, state in f.items():
        if state.alternatives and state.source != "user":
            issues.append(
                Issue(
                    field=key, severity="warning", message="Documents disagree on this value; confirm which is right."
                )
            )
        if state.uncertain and state.source != "user":
            issues.append(
                Issue(
                    field=key,
                    severity="warning",
                    message="Read from a hard-to-read source (e.g. handwriting); check it against the document.",
                )
            )

    for key in ("provider_npi", "referring_npi"):
        v = val(key)
        if v and not npi_is_valid(v):
            issues.append(
                Issue(
                    field=key, severity="warning", message="This NPI fails the NPI check-digit test; check for a typo."
                )
            )

    for code in filter(None, (c.strip() for c in val("icd10_codes").split(","))):
        if not ICD10_RE.fullmatch(code):
            issues.append(
                Issue(field="icd10_codes", severity="error", message=f"'{code}' is not a valid ICD-10 code format.")
            )
    for code in filter(None, (c.strip() for c in val("cpt_codes").split(","))):
        if not CPT_RE.match(code):
            issues.append(
                Issue(field="cpt_codes", severity="error", message=f"'{code}' is not a valid CPT/HCPCS code format.")
            )

    if val("tax_id") and not re.fullmatch(r"\d{2}-?\d{7}", val("tax_id")):
        issues.append(Issue(field="tax_id", severity="warning", message="Tax ID is usually 9 digits (XX-XXXXXXX)."))
    for key in ("payer_fax", "payer_phone", "member_phone", "provider_phone", "provider_fax", "referring_phone"):
        v = val(key)
        if v and len(digits(v)) not in (10, 11):
            issues.append(Issue(field=key, severity="warning", message="Phone/fax number doesn't have 10 digits."))

    for key in ("request_date", "member_dob", "start_date", "end_date", "signature_date"):
        v = val(key)
        if v and not parse_date(v):
            issues.append(Issue(field=key, severity="error", message="Not a date (use MM/DD/YYYY)."))
    start, end, dob = parse_date(val("start_date")), parse_date(val("end_date")), parse_date(val("member_dob"))
    if start and end and end <= start:
        issues.append(Issue(field="end_date", severity="error", message="End date must be after the start date."))
    if dob and dob >= date.today():
        issues.append(Issue(field="member_dob", severity="error", message="Date of birth is in the future."))

    if val("service_type") and val("service_type") not in SERVICE_TYPES:
        issues.append(
            Issue(field="service_type", severity="error", message="Pick one of the service types on the form.")
        )
    if val("sessions_units") and not re.fullmatch(r"\d+", val("sessions_units")):
        issues.append(
            Issue(field="sessions_units", severity="warning", message="Usually a whole number of sessions or units.")
        )

    if not case.form.assessments:
        issues.append(
            Issue(
                field="assessments",
                severity="warning",
                message="No standardized assessment scores; payers usually expect one (e.g. PHQ-9).",
            )
        )
    for row in case.form.medications + case.form.assessments:
        if row.uncertain and row.source != "user":
            issues.append(
                Issue(
                    field="medications" if "medication" in row.cells else "assessments",
                    severity="warning",
                    message=f"'{next(iter(row.cells.values()))}' was hard to read; check it against the document.",
                )
            )

    excluded = [d.filename for d in case.documents if not d.included]
    if excluded:
        issues.append(
            Issue(
                field=None,
                severity="warning",
                message="Not used because they are about a different patient: " + ", ".join(excluded),
            )
        )
    pending = [d.filename for d in case.documents if d.status in ("queued", "processing")]
    if pending:
        issues.append(Issue(field=None, severity="warning", message="Still reading: " + ", ".join(pending)))
    failed = [d.filename for d in case.documents if d.status == "failed"]
    if failed:
        issues.append(
            Issue(
                field=None,
                severity="error",
                message="Claude could not read these; retry or remove them: " + ", ".join(failed),
            )
        )
    if not f.get("signature") or not val("signature"):
        issues.append(
            Issue(
                field="signature",
                severity="warning",
                message="Not signed yet: the provider signs the printed form or applies a typed signature.",
            )
        )
    return issues
