from __future__ import annotations

import json

from app.claude.client import call_structured
from app.domain.models import NarrativeDraft

NARRATIVE_SYSTEM = """You draft the clinical narrative sections of a behavioral health prior-authorization \
request for a clinician to review and sign.

You get a JSON object with the facts already extracted from the patient's documents and the services \
being requested. Write each section as a payer reviewer expects: concise, clinical, specific.

Rules:
- Use only the facts provided. Do not invent symptoms, scores, dates, history, durations or risk. \
If something a reviewer would expect is missing, leave it out of the text and list it in `unsupported_gaps`.
- Cite scores with their instrument and date when available (e.g. "PHQ-9: 14 on 02/05/2026, down from 21").
- Treatment goals: measurable, tied to the documented problems and instruments, at most 3, each under 100 \
characters, no numbering.
- Respect the length limits in the schema descriptions; the paper form has a fixed number of lines.
- Plain text only, no markdown."""


async def draft_narrative(facts: dict) -> NarrativeDraft:
    return await call_structured(NARRATIVE_SYSTEM, json.dumps(facts, indent=1, default=str), NarrativeDraft)
