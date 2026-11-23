from __future__ import annotations

from pathlib import Path

import pymupdf as fitz


def open_document(path: Path) -> fitz.Document:
    doc = fitz.open(path)
    if not doc.is_pdf:
        pdf_bytes = doc.convert_to_pdf()
        doc.close()
        doc = fitz.open("pdf", pdf_bytes)
    return doc


def pdf_bytes(path: Path) -> bytes:
    with open_document(path) as doc:
        return doc.tobytes()


def render_page(path: Path, page_number: int, quote: str | None = None, dpi: int = 110) -> tuple[bytes, int]:
    with open_document(path) as doc:
        page_number = max(0, min(page_number, doc.page_count - 1))
        if quote:
            hit = _find_quote(doc, quote)
            if hit:
                page_number, rects = hit
                page = doc[page_number]
                for r in rects:
                    annot = page.add_highlight_annot(r)
                    annot.set_colors(stroke=(1, 0.85, 0.2))
                    annot.update()
        pix = doc[page_number].get_pixmap(dpi=dpi)
        return pix.tobytes("png"), page_number


def _find_quote(doc: fitz.Document, quote: str) -> tuple[int, list[fitz.Rect]] | None:
    q = " ".join(quote.split())

    candidates = [q] + [q[:n] for n in (80, 50, 30) if len(q) > n]
    if ": " in q:
        candidates.append(q.rsplit(": ", 1)[1])
    for cand in candidates:
        for i, page in enumerate(doc):
            rects = page.search_for(cand)
            if rects:
                return i, rects
    return None


def count_pages(data: bytes, content_type: str) -> int:
    filetype = "pdf" if content_type == "application/pdf" else content_type.split("/")[1]
    with fitz.open(stream=data, filetype=filetype) as doc:
        return doc.page_count
