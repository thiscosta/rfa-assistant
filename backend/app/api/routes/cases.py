from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import Response
from pydantic import BaseModel

from app.api.deps import case_view, load_case_or_404
from app.assembly.validation import validate
from app.documents.fill import render_pdf
from app.domain.models import Case, FieldState
from app.pipeline.processing import maybe_draft_narrative, reassemble
from app.storage import store

router = APIRouter()


class NewCase(BaseModel):
    label: str = ""


@router.get("/api/cases")
def list_cases() -> list[dict]:
    out = []
    for c in store.list_cases():
        issues = validate(c)
        out.append(
            {
                "id": c.id,
                "label": c.label,
                "member_name": c.form.fields.get("member_name", FieldState()).value,
                "payer": c.form.fields.get("payer", FieldState()).value,
                "documents": len(c.documents),
                "errors": sum(1 for i in issues if i.severity == "error"),
                "updated_at": c.updated_at.isoformat(),
            }
        )
    return out


@router.post("/api/cases")
def create_case(body: NewCase) -> dict:
    case = store.create_case(body.label.strip() or "New request")
    reassemble(case.id)
    return case_view(store.load_case(case.id))


@router.get("/api/cases/{case_id}")
def get_case(case_id: str) -> dict:
    return case_view(load_case_or_404(case_id))


@router.delete("/api/cases/{case_id}")
def delete_case(case_id: str) -> dict:
    load_case_or_404(case_id)
    store.delete_case(case_id)
    return {"ok": True}


class PrimaryPatient(BaseModel):
    key: str | None


@router.put("/api/cases/{case_id}/primary-patient")
def set_primary(case_id: str, body: PrimaryPatient, background: BackgroundTasks) -> dict:
    def apply(c: Case) -> None:
        c.primary_patient_key = body.key
        for d in c.documents:
            d.include_override = None

    store.update_case(case_id, apply)
    reassemble(case_id)
    background.add_task(maybe_draft_narrative, case_id)
    return case_view(store.load_case(case_id))


@router.post("/api/cases/{case_id}/narrative")
def redraft(case_id: str, background: BackgroundTasks) -> dict:
    load_case_or_404(case_id)
    background.add_task(maybe_draft_narrative, case_id, True)
    return case_view(store.update_case(case_id, lambda c: setattr(c, "narrative_status", "drafting")))


@router.get("/api/cases/{case_id}/pdf")
def download_pdf(case_id: str) -> Response:
    case = load_case_or_404(case_id)
    pdf = render_pdf(case)
    name = case.form.fields.get("member_name", FieldState()).value or case.label
    safe = "".join(ch if ch.isalnum() else "-" for ch in name).strip("-") or "request"
    return Response(
        pdf, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="RFA-{safe}.pdf"'}
    )
