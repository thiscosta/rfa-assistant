from __future__ import annotations

from dataclasses import asdict

from fastapi import HTTPException

from app.assembly.identity import patient_groups
from app.assembly.validation import validate
from app.domain.models import Case, CaseDocument
from app.storage import store


def get_document(case: Case, doc_id: str) -> CaseDocument:
    try:
        return case.document(doc_id)
    except KeyError:
        raise HTTPException(404, "Document not found") from None


def load_case_or_404(case_id: str) -> Case:
    try:
        return store.load_case(case_id)
    except KeyError:
        raise HTTPException(404, "Case not found") from None


def case_view(case: Case) -> dict:
    return {
        **case.model_dump(mode="json"),
        "issues": [i.model_dump() for i in validate(case)],
        "patient_groups": [asdict(g) for g in patient_groups(case)],
    }
