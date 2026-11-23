from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date

from app.domain.models import Alternative, Case, CaseDocument, DocumentExtraction, Evidence, FieldState, Quoted
from app.domain.normalize import comparable, parse_date

PRIORITY = {
    "demographics": ["intake_form", "referral_letter", "insurance_card", "clinical_note", "lab_report", "other"],
    "insurance": ["insurance_card", "intake_form", "referral_letter", "clinical_note", "lab_report", "other"],
    "clinical": ["clinical_note", "intake_form", "referral_letter", "other", "lab_report", "insurance_card"],
    "referral": ["referral_letter", "intake_form", "clinical_note", "other", "lab_report", "insurance_card"],
}


@dataclass
class Candidate:
    value: str
    evidence: Evidence
    uncertain: bool


def ranked_documents(case: Case, kind: str) -> list[CaseDocument]:
    rank = PRIORITY[kind]
    docs = [d for d in case.documents if d.included and d.extraction]

    def key(d: CaseDocument):
        ex = d.extraction
        assert ex
        dt = parse_date(ex.document_date) or date.min
        return (rank.index(ex.document_type), -dt.toordinal())

    return sorted(docs, key=key)


def evidence_from(doc: CaseDocument, quote: str) -> Evidence:
    return Evidence(doc_id=doc.id, doc_name=doc.filename, quote=quote)


def candidates_for(
    case: Case, kind: str, get: Callable[[DocumentExtraction], Quoted | None], norm: Callable[[str], str] = str.strip
) -> list[Candidate]:
    out = []
    for doc in ranked_documents(case, kind):
        assert doc.extraction
        q = get(doc.extraction)
        if q and q.value and q.value.strip():
            out.append(Candidate(norm(q.value), evidence_from(doc, q.quote), q.uncertain))
    return out


def field_from_candidates(cands: list[Candidate]) -> FieldState:
    if not cands:
        return FieldState()
    best = cands[0]
    agreeing = [c.evidence for c in cands if comparable(c.value) == comparable(best.value)]
    alternatives: list[Alternative] = []
    seen = {comparable(best.value)}
    for c in cands[1:]:
        k = comparable(c.value)
        if k not in seen:
            seen.add(k)
            alternatives.append(Alternative(value=c.value, evidence=c.evidence))
    return FieldState(
        value=best.value,
        source="document",
        evidence=agreeing,
        uncertain=best.uncertain,
        alternatives=alternatives,
        note="Documents disagree; pick the right value." if alternatives else None,
    )


def inferred_field(value: str, note: str, evidence: Iterable[Evidence] = ()) -> FieldState:
    if not value:
        return FieldState(note=note)
    return FieldState(value=value, source="inferred", note=note, evidence=list(evidence))


def profile_field(value: str) -> FieldState:
    return FieldState(value=value, source="clinic_profile") if value else FieldState()
