from __future__ import annotations

import re

from app.assembly.sources import evidence_from, ranked_documents
from app.domain.models import Case, Evidence, FieldState

DEFAULT_WEEKS = 12


START_OFFSET_DAYS = 7


_FREQ_PATTERNS: list[tuple[str, str, float]] = [
    (r"\b(2x|twice)\s*(/|a|per)?\s*(wk|week)|\btwice weekly\b", "2x/week", 2),
    (r"\b(3x|three times)\s*(/|a|per)?\s*(wk|week)", "3x/week", 3),
    (r"\b(bi-?weekly|every (2|two|other) weeks?)\b", "Every 2 weeks", 0.5),
    (r"\b(weekly|once (a|per) week|1x\s*/?\s*(wk|week)|q\s?wk)\b", "Weekly", 1),
    (r"\bmonthly|every (4|four) weeks\b", "Monthly", 0.25),
    (r"\b(5x|five times)\s*(/|a|per)?\s*(wk|week)|\bdaily\b", "5x/week", 5),
]


def parse_frequency(text: str) -> tuple[str, float] | None:
    t = text.lower()
    for pattern, label, per_week in _FREQ_PATTERNS:
        if re.search(pattern, t):
            return label, per_week
    return None


def parse_weeks(text: str) -> int | None:
    m = re.search(r"(\d+)\s*(weeks|wks|wk)\b", text.lower())
    if m:
        return int(m.group(1))
    m = re.search(r"(\d+)\s*months?\b", text.lower())
    if m:
        return int(m.group(1)) * 4
    return None


CPT_RULES: list[tuple[str, str, str]] = [
    (r"intensive outpatient|\biop\b", "S9480", "Intensive outpatient psychiatric services, per diem"),
    (
        r"psychiatric (evaluation|eval|assessment)|psych eval",
        "90792",
        "Psychiatric diagnostic evaluation with medical services",
    ),
    (r"diagnostic (evaluation|assessment)|intake assessment", "90791", "Psychiatric diagnostic evaluation"),
    (
        r"medication management|med management|medication follow|med f/u",
        "99214",
        "Office visit, established patient (medication management)",
    ),
    (r"group (therapy|psychotherapy)", "90853", "Group psychotherapy"),
    (r"family (therapy|psychotherapy)", "90847", "Family psychotherapy with patient"),
    (r"psychotherapy|therapy|\bcbt\b|\bemdr\b|counsel", "90837", "Psychotherapy, 60 minutes"),
]


def suggest_cpt(texts: list[str], service_type: str) -> list[tuple[str, str]]:
    codes: list[tuple[str, str]] = []
    for text in texts:
        t = text.lower()
        for pattern, code, label in CPT_RULES:
            if code == "S9480" and service_type != "Intensive Outpatient":
                continue
            if re.search(pattern, t) and code not in [c for c, _ in codes]:
                codes.append((code, label))
                if code in ("90837", "90853", "90847"):
                    break
    return codes


LEVEL_LABELS = {
    "outpatient": "Outpatient",
    "inpatient": "Inpatient",
    "intensive_outpatient": "Intensive Outpatient",
    "partial_hospitalization": "Partial Hospitalization",
    "residential": "Residential",
    "other": "Other",
}


SETTINGS = {
    "Outpatient": "Outpatient - Office",
    "Intensive Outpatient": "Intensive Outpatient Program",
    "Partial Hospitalization": "Partial Hospitalization Program",
    "Inpatient": "Inpatient - Hospital",
    "Residential": "Residential Treatment Facility",
}


def requested_service_texts(case: Case) -> tuple[list[str], list[Evidence]]:
    texts, evidence = [], []
    for doc in ranked_documents(case, "clinical"):
        ex = doc.extraction
        assert ex
        items = ex.services_requested or [
            q for q in ex.treatment_plan if re.search(r"therap|eval|medication|counsel|program|iop", q.value, re.I)
        ]
        for q in items:
            texts.append(q.value)
            evidence.append(evidence_from(doc, q.quote))
        if texts:
            break
    return texts, evidence


def frequency_field(case: Case, service_texts: list[str], service_evidence: list[Evidence]):
    weeks: int | None = None
    for doc in ranked_documents(case, "clinical"):
        ex = doc.extraction
        assert ex
        sources = (
            ([ex.requested_frequency] if ex.requested_frequency else []) + ex.services_requested + ex.treatment_plan
        )
        for q in sources:
            parsed = parse_frequency(q.value)
            if parsed:
                label, per_week = parsed
                ev = [evidence_from(doc, q.quote)]
                weeks = parse_weeks(q.value) or (
                    parse_weeks(ex.requested_duration.value) if ex.requested_duration else None
                )
                if weeks:
                    return FieldState(value=label, source="document", evidence=ev), per_week, weeks, ev
                return (
                    FieldState(value=label, source="document", evidence=ev),
                    per_week,
                    DEFAULT_WEEKS,
                    ev,
                )
    return FieldState(note="No frequency in the documents."), None, DEFAULT_WEEKS, []
