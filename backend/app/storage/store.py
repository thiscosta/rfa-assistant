from __future__ import annotations

import json
import shutil
import threading
import uuid
from collections import defaultdict
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import DATA_DIR
from app.domain.models import Case, ClinicProfile

_locks: dict[str, threading.RLock] = defaultdict(threading.RLock)


_locks_guard = threading.Lock()


def _lock(case_id: str) -> threading.RLock:
    with _locks_guard:
        return _locks[case_id]


def _cases_dir() -> Path:
    d = DATA_DIR / "cases"
    d.mkdir(parents=True, exist_ok=True)
    return d


def case_dir(case_id: str) -> Path:
    if not case_id.isalnum():
        raise KeyError(case_id)
    return _cases_dir() / case_id


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def create_case(label: str) -> Case:
    case = Case(id=new_id(), label=label)
    (case_dir(case.id) / "docs").mkdir(parents=True, exist_ok=True)
    save_case(case)
    return case


def load_case(case_id: str) -> Case:
    path = case_dir(case_id) / "case.json"
    if not path.exists():
        raise KeyError(case_id)
    return Case.model_validate_json(path.read_text())


def save_case(case: Case) -> None:
    case.updated_at = datetime.now(UTC)
    path = case_dir(case.id) / "case.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(case.model_dump_json(indent=2))
    tmp.replace(path)


@contextmanager
def editing(case_id: str) -> Iterator[Case]:
    with _lock(case_id):
        case = load_case(case_id)
        yield case
        save_case(case)


def update_case(case_id: str, fn: Callable[[Case], None]) -> Case:
    with editing(case_id) as case:
        fn(case)
    return case


def list_cases() -> list[Case]:
    cases = []
    for d in _cases_dir().iterdir():
        if (d / "case.json").exists():
            cases.append(Case.model_validate_json((d / "case.json").read_text()))
    return sorted(cases, key=lambda c: c.updated_at, reverse=True)


def delete_case(case_id: str) -> None:
    with _lock(case_id):
        shutil.rmtree(case_dir(case_id), ignore_errors=True)


def document_path(case_id: str, doc_id: str, filename: str) -> Path:
    suffix = Path(filename).suffix.lower() or ".bin"
    return case_dir(case_id) / "docs" / f"{doc_id}{suffix}"


def _profile_path() -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR / "clinic.json"


def load_profile() -> ClinicProfile:
    p = _profile_path()
    if not p.exists():
        return ClinicProfile()
    return ClinicProfile.model_validate(json.loads(p.read_text()))


def save_profile(profile: ClinicProfile) -> None:
    _profile_path().write_text(profile.model_dump_json(indent=2))
