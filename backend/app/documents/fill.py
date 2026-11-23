from __future__ import annotations

from dataclasses import dataclass

import pymupdf as fitz

from app.core.config import TEMPLATE_PDF
from app.domain.form_schema import ASSESSMENT_ROWS_ON_FORM, FIELDS, MEDICATION_ROWS_ON_FORM, FormField
from app.domain.models import Case

INK = (0, 0.2, 0.4)


FONT = "cour"


RIGHT_EDGE = 560.8


HEADER_SPLIT_X = 300.0


LINE_GAP = 16.0


CONTINUED = "(continued on addendum)"


MED_COLS = (55.2, 182.6, 310.0, 437.4)


ASSESS_COLS = (55.2, 225.1, 394.9)


TABLE_FIRST_LINE_OFFSET = 19.5


@dataclass
class Overflow:
    title: str
    text: str


def _label_rect(page: fitz.Page, label: str, occurrence: int) -> fitz.Rect:
    hits = []
    for r in page.search_for(label):
        mid = (r.y0 + r.y1) / 2
        # Skip matches inside a longer label, e.g. "Phone:" within "Payer Phone:".
        left = page.get_textbox(fitz.Rect(r.x0 - 25, mid - 1, r.x0 - 0.5, mid + 1)).strip()
        if not left:
            hits.append(r)
    hits.sort(key=lambda r: (round(r.y0), r.x0))
    if occurrence >= len(hits):
        raise LookupError(f"Label {label!r} (#{occurrence}) not found on the template")
    return hits[occurrence]


def _fit(text: str, max_width: float, size: float) -> tuple[str, float, bool]:
    while size > 6.5 and fitz.get_text_length(text, FONT, size) > max_width:
        size -= 0.5
    if fitz.get_text_length(text, FONT, size) <= max_width:
        return text, size, False
    suffix = " " + CONTINUED
    while text and fitz.get_text_length(text + suffix, FONT, size) > max_width:
        text = text[:-1]
    return text.rstrip() + suffix, size, True


def _wrap(text: str, max_width: float, size: float, first_width: float | None = None) -> list[str]:
    lines: list[str] = []
    for paragraph in text.splitlines() or [""]:
        cur = ""
        for w in paragraph.split():
            width = first_width if (first_width is not None and not lines) else max_width
            cand = f"{cur} {w}".strip()
            if fitz.get_text_length(cand, FONT, size) <= width or not cur:
                cur = cand
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
    return lines


def _put(page: fitz.Page, x: float, baseline: float, text: str, size: float = 9) -> None:
    page.insert_text((x, baseline), text, fontname=FONT, fontsize=size, color=INK)


def _fill_line(page: fitz.Page, field: FormField, value: str, overflow: list[Overflow]) -> None:
    r = _label_rect(page, field.label, field.occurrence)
    x = r.x1 + 6
    right = HEADER_SPLIT_X if (field.section == "header" and r.x0 < HEADER_SPLIT_X) else RIGHT_EDGE
    baseline, size = r.y1 - 2.5, 9.0
    # On the template these two rows sit partly under the Section A bar.
    if field.key in ("payer_fax", "payer_phone"):
        baseline, size = r.y0 + 4.2, 8.0
    text, size, truncated = _fit(value, right - x, size)
    _put(page, x, baseline, text, size)
    if truncated:
        overflow.append(Overflow(field.label.rstrip(":"), value))


def _fill_block(page: fitz.Page, field: FormField, value: str, overflow: list[Overflow]) -> None:
    r = _label_rect(page, field.label, field.occurrence)
    size, left = 8.0, 55.2
    full = RIGHT_EDGE - left - 2
    first_x = r.x1 + 6
    lines = _wrap(value, full, size, first_width=RIGHT_EDGE - first_x - 2)
    first_rule = r.y1 + 3.5
    if len(lines) > field.lines:
        lines = lines[: field.lines]
        width = full if field.lines > 1 else RIGHT_EDGE - first_x - 2
        words = lines[-1].split()
        while words and fitz.get_text_length(" ".join(words + [CONTINUED]), FONT, size) > width:
            words.pop()
        lines[-1] = " ".join(words + [CONTINUED])
        overflow.append(Overflow(field.label.rstrip(":?"), value))
    for i, line in enumerate(lines):
        _put(page, first_x if i == 0 else left, first_rule + i * LINE_GAP - 2, line, size)


def _fill_table(
    page: fitz.Page,
    label: str,
    cols: tuple[float, ...],
    keys: tuple[str, ...],
    rows: list[dict],
    max_rows: int,
    title: str,
    overflow: list[Overflow],
) -> None:
    r = _label_rect(page, label, 0)
    first_rule = r.y1 + TABLE_FIRST_LINE_OFFSET
    shown = rows if len(rows) <= max_rows else rows[: max_rows - 1]
    for i, row in enumerate(shown):
        for j, key in enumerate(keys):
            right = cols[j + 1] - 4 if j + 1 < len(cols) else RIGHT_EDGE - 2
            text, size, _ = _fit(row.get(key, ""), right - cols[j], 8.0)
            _put(page, cols[j], first_rule + i * LINE_GAP - 3.5, text, size)
    if len(rows) > max_rows:
        _put(
            page,
            cols[0],
            first_rule + (max_rows - 1) * LINE_GAP - 3.5,
            f"+{len(rows) - len(shown)} more {CONTINUED}",
            8.0,
        )
        overflow.append(Overflow(title, "\n".join("  |  ".join(row.get(k, "") for k in keys) for row in rows)))


def _check_service_type(page: fitz.Page, value: str) -> None:
    if not value:
        return
    r = _label_rect(page, value, 0)
    page.insert_text((r.x0 - 10, r.y1 - 0.5), "X", fontname="hebo", fontsize=10, color=INK)


def _addendum(doc: fitz.Document, case: Case, overflow: list[Overflow]) -> None:
    f = case.form.fields
    width, height = doc[0].rect.width, doc[0].rect.height
    page = doc.new_page(width=width, height=height)
    y = 50.0
    page.insert_text(
        (51.2, y), "ADDENDUM - REQUEST FOR APPROVAL OF SERVICES", fontname="hebo", fontsize=12, color=(0.1, 0.23, 0.36)
    )
    y += 16
    ident = f"Member: {f['member_name'].value}   DOB: {f['member_dob'].value}   Member ID: {f['member_id'].value}"
    page.insert_text((51.2, y), ident, fontname="helv", fontsize=8, color=(0.2, 0.2, 0.2))
    y += 18
    for item in overflow:
        lines = _wrap(item.text, RIGHT_EDGE - 55.2, 8.5)
        needed = 14 + len(lines) * 11 + 8
        if y + needed > height - 40:
            page = doc.new_page(width=width, height=height)
            y = 50.0
        page.insert_text((51.2, y), item.title, fontname="hebo", fontsize=8.5, color=(0.1, 0.23, 0.36))
        y += 13
        for line in lines:
            _put(page, 55.2, y, line, 8.5)
            y += 11
        y += 8


def render_pdf(case: Case) -> bytes:
    doc = fitz.open(TEMPLATE_PDF)
    f = case.form.fields
    overflow: list[Overflow] = []
    for field in FIELDS:
        value = f[field.key].value.strip() if field.key in f else ""
        if not value:
            continue
        page = doc[field.page]
        if field.kind == "choice":
            _check_service_type(page, value)
        elif field.kind == "longtext":
            _fill_block(page, field, value, overflow)
        else:
            _fill_line(page, field, value, overflow)

    page2 = doc[1]
    _fill_table(
        page2,
        "Current medications:",
        MED_COLS,
        ("medication", "dose", "frequency", "prescriber"),
        [r.cells for r in case.form.medications],
        MEDICATION_ROWS_ON_FORM,
        "Current medications",
        overflow,
    )
    _fill_table(
        page2,
        "Most recent validated assessment scores:",
        ASSESS_COLS,
        ("tool", "score", "date"),
        [r.cells for r in case.form.assessments],
        ASSESSMENT_ROWS_ON_FORM,
        "Most recent validated assessment scores",
        overflow,
    )

    if overflow:
        _addendum(doc, case, overflow)
    out = doc.tobytes(garbage=3, deflate=True)
    doc.close()
    return out
