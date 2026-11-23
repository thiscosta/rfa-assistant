from __future__ import annotations

from fastapi import APIRouter

from app.domain.models import ClinicProfile
from app.pipeline.processing import reassemble
from app.storage import store

router = APIRouter()


@router.get("/api/clinic")
def get_clinic() -> ClinicProfile:
    return store.load_profile()


@router.put("/api/clinic")
def put_clinic(profile: ClinicProfile) -> ClinicProfile:
    store.save_profile(profile)
    for case in store.list_cases():
        reassemble(case.id)
    return profile
