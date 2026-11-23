from __future__ import annotations

import hashlib
import json
from datetime import date

from app.assembly.sources import evidence_from, ranked_documents
from app.domain.models import Case, Evidence, FieldState, TableRow
from app.domain.normalize import normalize_date, parse_date

NARRATIVE_FIELDS = (
    "presenting_symptoms",
    "clinical_history",
    "treatment_goals",
    "medical_necessity",
    "risk_without_services",
)


def diagnosis_codes(case: Case) -> tuple[list[str], list[str], list[Evidence]]:
    rows: list[tuple[str, str, Evidence]] = []
    seen: set[str] = set()
    docs = ranked_documents(case, "clinical")
    for roles in (("reason_for_services",), ("comorbid",)):
        for doc in docs:
            for dx in doc.extraction.diagnoses:  # type: ignore[union-attr]
                if dx.role not in roles:
                    continue
                k = (dx.code or dx.description).upper().strip()
                if k in seen:
                    continue
                seen.add(k)
                rows.append((dx.code or "", dx.description, evidence_from(doc, dx.quote)))
        if rows:
            break
    return [r[0] for r in rows], [r[1] for r in rows], [r[2] for r in rows]


def medication_rows(case: Case) -> list[TableRow]:
    rows: list[TableRow] = []
    seen: set[str] = set()
    for doc in ranked_documents(case, "clinical"):
        for m in doc.extraction.medications:  # type: ignore[union-attr]
            k = (m.generic_name or m.name).lower()
            if k in seen or m.name.lower() in seen:
                continue
            seen.update({k, m.name.lower()})
            name = (
                m.name
                if not m.generic_name or m.generic_name.lower() == m.name.lower()
                else f"{m.name} ({m.generic_name})"
            )
            rows.append(
                TableRow(
                    cells={
                        "medication": name,
                        "dose": m.dose or "",
                        "frequency": m.frequency or "",
                        "prescriber": m.prescriber or "",
                    },
                    evidence=[evidence_from(doc, m.quote)],
                    uncertain=m.uncertain,
                )
            )
    return rows


def assessment_rows(case: Case) -> list[TableRow]:
    rows: list[TableRow] = []
    seen: set[tuple[str, str, str]] = set()
    for doc in ranked_documents(case, "clinical"):
        ex = doc.extraction
        assert ex
        for a in ex.assessments:
            when = normalize_date(a.date or ex.document_date or "")
            k = (a.tool.upper(), a.score, when)
            if k in seen:
                continue
            seen.add(k)
            score = f"{a.score} ({a.interpretation})" if a.interpretation else a.score
            rows.append(
                TableRow(
                    cells={"tool": a.tool, "score": score, "date": when},
                    evidence=[evidence_from(doc, a.quote)],
                    uncertain=a.uncertain,
                )
            )
    return rows


def latest_per_tool(rows: list[TableRow]) -> list[TableRow]:
    best: dict[str, TableRow] = {}
    for r in rows:
        tool = r.cells["tool"].upper()
        cur = best.get(tool)
        if cur is None or (parse_date(r.cells["date"]) or date.min) > (parse_date(cur.cells["date"]) or date.min):
            best[tool] = r
    return list(best.values())


def quotes(case: Case, attr: str) -> list[str]:
    out: list[str] = []
    for doc in ranked_documents(case, "clinical"):
        for q in getattr(doc.extraction, attr):
            if q.value not in out:
                out.append(q.value)
    return out


def narrative_facts(case: Case, f: dict[str, FieldState], meds: list[TableRow], scores: list[TableRow]) -> dict:
    dob = parse_date(f["member_dob"].value)
    age = None
    if dob:
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    notes: list[str] = []
    for doc in ranked_documents(case, "clinical"):
        notes.extend(doc.extraction.reading_notes)  # type: ignore[union-attr]
    return {
        "patient": {"age": age, "gender": f["member_gender"].value or None},
        "diagnoses": f["diagnosis_descriptions"].value,
        "icd10_codes": f["icd10_codes"].value,
        "requested_service": {
            "type": f["service_type"].value,
            "cpt_codes": f["cpt_codes"].value,
            "frequency": f["frequency"].value,
            "sessions": f["sessions_units"].value,
            "start": f["start_date"].value,
            "end": f["end_date"].value,
        },
        "assessments": [r.cells for r in scores],
        "medications": [r.cells for r in meds],
        "symptoms": quotes(case, "symptoms"),
        "functional_impairment": quotes(case, "functional_impairment"),
        "clinical_history": quotes(case, "clinical_history"),
        "risk_factors": quotes(case, "risk_factors"),
        "treatment_plan": quotes(case, "treatment_plan"),
        "services_requested": quotes(case, "services_requested"),
        "reading_notes": notes,
    }


def facts_hash(facts: dict) -> str:
    return hashlib.sha256(json.dumps(facts, sort_keys=True, default=str).encode()).hexdigest()[:16]
