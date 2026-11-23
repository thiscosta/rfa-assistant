from __future__ import annotations

from dataclasses import dataclass

from app.assembly.sources import PRIORITY
from app.domain.models import Case
from app.domain.normalize import patient_key


def same_patient(a: str | None, b: str | None) -> bool:
    if not a or not b:
        return True
    la, da = a.split("|")
    lb, db = b.split("|")
    return la == lb and (da == db or "?" in (da, db))


@dataclass
class PatientGroup:
    key: str
    name: str
    dob: str
    doc_ids: list[str]


def patient_groups(case: Case) -> list[PatientGroup]:
    groups: list[PatientGroup] = []
    for doc in case.documents:
        ex = doc.extraction
        if not ex or not doc.patient_key:
            continue
        group = next((g for g in groups if same_patient(g.key, doc.patient_key)), None)
        name = ex.patient.full_name.value if ex.patient.full_name else ""
        dob = ex.patient.date_of_birth.value if ex.patient.date_of_birth else ""
        if group is None:
            groups.append(PatientGroup(doc.patient_key, name, dob, [doc.id]))
        else:
            group.doc_ids.append(doc.id)
            if "?" in group.key and "?" not in doc.patient_key:
                group.key = doc.patient_key
            group.name = group.name or name
            group.dob = group.dob or dob
    return groups


def resolve_identity(case: Case) -> None:
    for doc in case.documents:
        ex = doc.extraction
        doc.patient_key = (
            patient_key(
                ex.patient.full_name.value if ex.patient.full_name else None,
                ex.patient.date_of_birth.value if ex.patient.date_of_birth else None,
            )
            if ex
            else None
        )
    groups = patient_groups(case)
    primary = case.primary_patient_key
    if primary and not any(same_patient(g.key, primary) for g in groups):
        primary = None
    if not primary and groups:
        rank = PRIORITY["clinical"]

        def score(g: PatientGroup) -> tuple:
            types = [d.extraction.document_type for d in case.documents if d.id in g.doc_ids and d.extraction]
            best = min((rank.index(t) for t in types), default=len(rank))
            return (-len(g.doc_ids), best)

        primary = sorted(groups, key=score)[0].key
    for doc in case.documents:
        auto = same_patient(doc.patient_key, primary) if primary else True
        doc.included = doc.include_override if doc.include_override is not None else auto
