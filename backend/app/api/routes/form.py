from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.deps import case_view
from app.domain.form_schema import FIELDS_BY_KEY
from app.domain.models import Case, FieldState, TableRow
from app.pipeline.processing import reassemble
from app.storage import store

router = APIRouter()


class FieldsPatch(BaseModel):
    updates: dict[str, str] = {}
    reset: list[str] = []


@router.patch("/api/cases/{case_id}/fields")
def patch_fields(case_id: str, body: FieldsPatch) -> dict:
    unknown = [k for k in [*body.updates, *body.reset] if k not in FIELDS_BY_KEY]
    if unknown:
        raise HTTPException(422, f"Unknown fields: {unknown}")

    def apply(c: Case) -> None:
        for key, value in body.updates.items():
            old = c.form.fields.get(key, FieldState())
            c.form.fields[key] = FieldState(
                value=value, source="user", evidence=old.evidence if value == old.value else []
            )
        for key in body.reset:
            c.form.fields[key] = FieldState()

    store.update_case(case_id, apply)
    reassemble(case_id)
    return case_view(store.load_case(case_id))


class TablePut(BaseModel):
    rows: list[dict[str, str]]


@router.put("/api/cases/{case_id}/tables/{table}")
def put_table(case_id: str, table: str, body: TablePut) -> dict:
    if table not in ("medications", "assessments"):
        raise HTTPException(404, "Unknown table")

    def apply(c: Case) -> None:
        old = getattr(c.form, table)
        rows = []
        for i, cells in enumerate(body.rows):
            prev = old[i] if i < len(old) else None
            same = prev is not None and prev.cells == cells
            rows.append(prev if same else TableRow(cells=cells, source="user"))
        setattr(c.form, table, rows)
        setattr(c.form, f"{table}_edited", True)

    store.update_case(case_id, apply)
    reassemble(case_id)
    return case_view(store.load_case(case_id))


@router.delete("/api/cases/{case_id}/tables/{table}")
def reset_table(case_id: str, table: str) -> dict:
    if table not in ("medications", "assessments"):
        raise HTTPException(404, "Unknown table")
    store.update_case(case_id, lambda c: setattr(c.form, f"{table}_edited", False))
    reassemble(case_id)
    return case_view(store.load_case(case_id))


class SignatureBody(BaseModel):
    typed: bool


@router.post("/api/cases/{case_id}/signature")
def signature(case_id: str, body: SignatureBody) -> dict:
    store.update_case(case_id, lambda c: setattr(c, "typed_signature", body.typed))
    reassemble(case_id)
    return case_view(store.load_case(case_id))
