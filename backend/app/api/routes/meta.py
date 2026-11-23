from __future__ import annotations

from fastapi import APIRouter

from app.core.config import CLAUDE_MODEL
from app.core.credentials import credential_source
from app.domain.form_schema import schema_payload

router = APIRouter()


@router.get("/api/health")
def health() -> dict:
    source = credential_source()
    return {"ok": source is not None, "model": CLAUDE_MODEL, "credential": source}


@router.get("/api/form-schema")
def form_schema() -> dict:
    return schema_payload()
