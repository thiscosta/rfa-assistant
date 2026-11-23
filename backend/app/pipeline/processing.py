from __future__ import annotations

import asyncio
import logging

from app.assembly.assemble import assemble
from app.assembly.clinical import facts_hash
from app.claude.client import ClaudeError
from app.claude.extraction import extract_document
from app.claude.narrative import draft_narrative
from app.documents.source import pdf_bytes
from app.domain.models import Case
from app.storage import store

log = logging.getLogger("rfa")


def reassemble(case_id: str) -> dict:
    profile = store.load_profile()
    with store.editing(case_id) as case:
        case.form, facts = assemble(case, profile)
    return facts


async def process_document(case_id: str, doc_id: str) -> None:
    with store.editing(case_id) as case:
        doc = case.document(doc_id)
        doc.status, doc.error = "processing", None
        path = store.document_path(case_id, doc.id, doc.filename)
        filename = doc.filename

    extraction, error = None, None
    try:
        extraction = await extract_document(await asyncio.to_thread(pdf_bytes, path), filename)
    except ClaudeError as e:
        log.warning("claude extraction failed for %s: %s", filename, e)
        error = str(e)
    except Exception as e:  # noqa: BLE001 - surface any failure on the document instead of losing it
        log.exception("processing %s failed", filename)
        error = f"Could not read the file: {e}"

    with store.editing(case_id) as case:
        doc = case.document(doc_id)
        doc.extraction, doc.error = extraction, error
        doc.status = "extracted" if extraction else "failed"
    reassemble(case_id)


async def process_documents(case_id: str, doc_ids: list[str]) -> None:
    await asyncio.gather(*(process_document(case_id, d) for d in doc_ids))
    await maybe_draft_narrative(case_id)


async def maybe_draft_narrative(case_id: str, force: bool = False) -> None:
    case = store.load_case(case_id)
    if any(d.status in ("queued", "processing") for d in case.documents):
        return
    facts = reassemble(case_id)
    h = facts_hash(facts)
    if not force and case.narrative_facts_hash == h and case.narrative_draft:
        return
    if not facts.get("diagnoses") and not facts.get("symptoms"):
        return
    store.update_case(case_id, lambda c: setattr(c, "narrative_status", "drafting"))
    try:
        draft = await draft_narrative(facts)
    except ClaudeError as e:
        message = str(e)

        def failed(c: Case) -> None:
            c.narrative_status, c.narrative_error = "failed", message

        store.update_case(case_id, failed)
        return

    def done(c: Case) -> None:
        c.narrative_draft, c.narrative_facts_hash = draft, h
        c.narrative_status, c.narrative_error = "done", None

    store.update_case(case_id, done)
    reassemble(case_id)


def resume_interrupted() -> None:
    for case in store.list_cases():
        pending = [d.id for d in case.documents if d.status in ("queued", "processing")]
        if pending:
            asyncio.create_task(process_documents(case.id, pending))
