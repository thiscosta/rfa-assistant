from __future__ import annotations

import base64

from app.claude.client import call_structured
from app.claude.schema import FIELD_GUIDE, ClaudeExtraction, to_extraction
from app.domain.models import DocumentExtraction

EXTRACTION_SYSTEM = (
    """You read clinical and administrative documents for a behavioral health clinic \
that is preparing a prior-authorization request ("Request for Approval of Services").

Extract what the document actually says into the schema: identity, insurance and provider details and narrative points go in `facts` as {field, value, quote}; diagnoses, medications and standardized scores go in their own lists.

Rules:
- Only record what is written. Never fill a field from general knowledge or a guess about what is typical. \
Leave a fact out, use "" for an unknown sub-field, or an empty list when the document is silent. Use level_of_care "not_stated" unless the document names one.
- Every value carries `quote`: the shortest verbatim passage from the document that supports it, copied \
character for character (keep abbreviations and typos). For handwriting, quote your best reading.
- Set `uncertain: true` when the handwriting, scan quality or wording leaves real doubt about the value, \
and explain the doubt in `reading_notes`.
- Normalize values (not quotes): dates as MM/DD/YYYY (two-digit years: 20xx unless that is in the future \
for a birth date), phone numbers as (XXX) XXX-XXXX.
- Expand clinical shorthand in values where it is unambiguous (e.g. "f/u" -> "follow-up", "SI/HI" -> \
"suicidal/homicidal ideation"), but keep the quote verbatim.
- Diagnoses: keep ICD-10 codes exactly as written. Mark `reason_for_services` only for conditions the \
behavioral health services would treat; medical conditions are `comorbid`.
- Medications: list current medications. Fill `generic_name` for brand names you are sure about \
(e.g. Lexapro -> escitalopram).
- Assessments: standardized instruments only (PHQ-9, GAD-7, PCL-5, AUDIT, ...). Include earlier scores \
mentioned for comparison as separate entries with their own dates when given.
- Insurance cards: the payer is the insurance company; prefer a behavioral or mental health phone number \
for `payer_phone` when the card lists one.

"""
    + FIELD_GUIDE
)


async def extract_document(pdf: bytes, filename: str) -> DocumentExtraction:
    content = [
        {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": base64.standard_b64encode(pdf).decode("ascii"),
            },
            "title": filename,
        },
        {"type": "text", "text": f"Extract the facts from '{filename}'."},
    ]
    return to_extraction(await call_structured(EXTRACTION_SYSTEM, content, ClaudeExtraction))
