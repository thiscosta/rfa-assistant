from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from app.api.deps import case_view, get_document, load_case_or_404
from app.core.config import ACCEPTED_TYPES, MAX_UPLOAD_BYTES
from app.core.credentials import MissingCredentials, require_credentials
from app.documents.source import count_pages, render_page
from app.domain.models import CaseDocument
from app.pipeline.processing import maybe_draft_narrative, process_documents, reassemble
from app.storage import store

router = APIRouter()


@router.post("/api/cases/{case_id}/documents")
async def upload(case_id: str, background: BackgroundTasks, files: list[UploadFile] = File(...)) -> dict:
    load_case_or_404(case_id)
    try:
        require_credentials()
    except MissingCredentials as e:
        raise HTTPException(503, str(e)) from e
    new_ids = []
    for upload in files:
        ctype = upload.content_type or ""
        if ctype not in ACCEPTED_TYPES:
            raise HTTPException(415, f"{upload.filename}: only PDF, PNG and JPEG files are accepted")
        data = await upload.read()
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, f"{upload.filename}: file is larger than 25 MB")
        doc = CaseDocument(id=store.new_id(), filename=upload.filename or "document", content_type=ctype)
        store.document_path(case_id, doc.id, doc.filename).write_bytes(data)
        try:
            doc.page_count = count_pages(data, ctype)
        except Exception:  # noqa: BLE001
            raise HTTPException(422, f"{upload.filename}: the file could not be opened") from None
        store.update_case(case_id, lambda c, doc=doc: c.documents.append(doc))
        new_ids.append(doc.id)
    background.add_task(process_documents, case_id, new_ids)
    return case_view(store.load_case(case_id))


@router.post("/api/cases/{case_id}/documents/{doc_id}/retry")
def retry(case_id: str, doc_id: str, background: BackgroundTasks) -> dict:
    store.update_case(case_id, lambda c: setattr(get_document(c, doc_id), "status", "queued"))
    background.add_task(process_documents, case_id, [doc_id])
    return case_view(store.load_case(case_id))


@router.delete("/api/cases/{case_id}/documents/{doc_id}")
async def delete_document(case_id: str, doc_id: str, background: BackgroundTasks) -> dict:
    case = load_case_or_404(case_id)
    doc = get_document(case, doc_id)
    store.document_path(case_id, doc.id, doc.filename).unlink(missing_ok=True)
    store.update_case(case_id, lambda c: setattr(c, "documents", [d for d in c.documents if d.id != doc_id]))
    reassemble(case_id)
    background.add_task(maybe_draft_narrative, case_id)
    return case_view(store.load_case(case_id))


class DocumentPatch(BaseModel):
    include_override: bool | None = None


@router.patch("/api/cases/{case_id}/documents/{doc_id}")
def patch_document(case_id: str, doc_id: str, body: DocumentPatch, background: BackgroundTasks) -> dict:
    store.update_case(case_id, lambda c: setattr(get_document(c, doc_id), "include_override", body.include_override))
    reassemble(case_id)
    background.add_task(maybe_draft_narrative, case_id)
    return case_view(store.load_case(case_id))


@router.get("/api/cases/{case_id}/documents/{doc_id}/file")
def document_file(case_id: str, doc_id: str) -> FileResponse:
    doc = get_document(load_case_or_404(case_id), doc_id)
    return FileResponse(
        store.document_path(case_id, doc.id, doc.filename), media_type=doc.content_type, filename=doc.filename
    )


@router.get("/api/cases/{case_id}/documents/{doc_id}/preview")
def document_preview(case_id: str, doc_id: str, page: int = 0, quote: str | None = None) -> Response:
    doc = get_document(load_case_or_404(case_id), doc_id)
    png, shown = render_page(store.document_path(case_id, doc.id, doc.filename), page, quote)
    return Response(png, media_type="image/png", headers={"X-Page": str(shown), "Cache-Control": "no-store"})
