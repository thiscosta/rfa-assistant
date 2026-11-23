from __future__ import annotations

from collections.abc import Callable

from app.assembly.sources import evidence_from, ranked_documents
from app.domain.models import (
    Case,
    CaseDocument,
    ClinicProfile,
    ClinicProvider,
    DocumentExtraction,
    FieldState,
    ProviderInfo,
    Quoted,
)
from app.domain.normalize import name_tokens


def best_provider(case: Case, kind: str, get: Callable[[DocumentExtraction], ProviderInfo | None]):
    for doc in ranked_documents(case, kind):
        p = get(doc.extraction)  # type: ignore[arg-type]
        if p and (p.name or p.npi):
            return doc, p
    return None, None


def provider_field(doc: CaseDocument | None, p: ProviderInfo | None, attr: str, norm=str.strip) -> FieldState:
    if not doc or not p:
        return FieldState()
    q: Quoted | None = getattr(p, attr)
    if not q or not q.value:
        return FieldState()
    return FieldState(
        value=norm(q.value), source="document", evidence=[evidence_from(doc, q.quote)], uncertain=q.uncertain
    )


def match_clinic_provider(profile: ClinicProfile, treating: ProviderInfo | None) -> ClinicProvider | None:
    if treating:
        npi = treating.npi.value if treating.npi else ""
        last = (name_tokens(treating.name.value) or [""])[-1] if treating.name else ""
        for p in profile.providers:
            if npi and p.npi and npi == p.npi:
                return p
            if last and name_tokens(p.name) and name_tokens(p.name)[-1] == last:
                return p
        return None
    if profile.default_provider_index is not None and 0 <= profile.default_provider_index < len(profile.providers):
        return profile.providers[profile.default_provider_index]
    return None


def same_provider(p: ProviderInfo, name: str, npi: str) -> bool:
    if p.npi and npi and p.npi.value == npi:
        return True
    a, b = name_tokens(p.name.value if p.name else ""), name_tokens(name)
    return bool(a and b and a[-1] == b[-1])
