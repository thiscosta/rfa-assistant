from __future__ import annotations

import os
import tempfile
from pathlib import Path

os.environ["RFA_DATA_DIR"] = tempfile.mkdtemp(prefix="rfa-test-")
os.environ["ANTHROPIC_API_KEY"] = "test-key-never-sent"

import pymupdf  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import main  # noqa: E402
from app.claude.client import ClaudeError  # noqa: E402
from app.core import credentials  # noqa: E402
from app.core.credentials import MissingCredentials  # noqa: E402
from app.domain.models import DocumentExtraction, NarrativeDraft  # noqa: E402
from app.domain.normalize import member_name_last_first, npi_is_valid, patient_key  # noqa: E402
from app.pipeline import processing  # noqa: E402

SAMPLES = Path(__file__).resolve().parents[2] / "samples"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
client = TestClient(main.app)


@pytest.fixture(autouse=True)
def recorded_claude(monkeypatch):
    calls: list[str] = []

    async def extract(pdf: bytes, filename: str) -> DocumentExtraction:
        calls.append(filename)
        path = FIXTURES / f"{Path(filename).stem}.extraction.json"
        if not path.exists():
            raise ClaudeError("Could not reach the Claude API.")
        return DocumentExtraction.model_validate_json(path.read_text())

    async def draft(facts: dict) -> NarrativeDraft:
        calls.append("narrative")
        return NarrativeDraft.model_validate_json(
            (FIXTURES / "06-handwritten-clinical-note.narrative.json").read_text()
        )

    monkeypatch.setattr(processing, "extract_document", extract)
    monkeypatch.setattr(processing, "draft_narrative", draft)
    return calls


def _case() -> str:
    return client.post("/api/cases", json={"label": "test"}).json()["id"]


def _upload(case_id: str, *names: str, data: bytes | None = None) -> dict:
    files = [("files", (n, data or (SAMPLES / n).read_bytes(), "application/pdf")) for n in names]
    r = client.post(f"/api/cases/{case_id}/documents", files=files)
    assert r.status_code == 200, r.text
    return client.get(f"/api/cases/{case_id}").json()


def _v(case: dict, key: str) -> str:
    return case["form"]["fields"][key]["value"]


def test_server_refuses_to_start_without_claude_credentials(monkeypatch, tmp_path):
    for var in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_PROFILE"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ANTHROPIC_CONFIG_DIR", str(tmp_path))
    with pytest.raises(MissingCredentials, match="ant auth login"):
        with TestClient(main.app):
            pass


def test_uploads_are_refused_if_credentials_disappear(monkeypatch, tmp_path):
    cid = _case()
    monkeypatch.delenv("ANTHROPIC_API_KEY")
    monkeypatch.setenv("ANTHROPIC_CONFIG_DIR", str(tmp_path))
    r = client.post(f"/api/cases/{cid}/documents", files=[("files", ("a.pdf", b"%PDF", "application/pdf"))])
    assert r.status_code == 503 and "Claude credentials are required" in r.json()["detail"]
    assert client.get(f"/api/cases/{cid}").json()["documents"] == []


def test_a_claude_failure_fails_the_document_with_no_fallback():
    cid = _case()
    case = _upload(cid, "unknown.pdf", data=(SAMPLES / "02-referral-letter.pdf").read_bytes())
    doc = case["documents"][0]
    assert doc["status"] == "failed" and doc["extraction"] is None
    assert doc["error"] == "Could not reach the Claude API."
    assert _v(case, "member_name") == ""
    assert any("Claude could not read" in i["message"] for i in case["issues"])


def test_narrative_sections_stay_empty_until_claude_drafts_them(monkeypatch):
    async def fail(facts: dict) -> NarrativeDraft:
        raise ClaudeError("Claude API error 529: overloaded")

    monkeypatch.setattr(processing, "draft_narrative", fail)
    cid = _case()
    case = _upload(cid, "06-handwritten-clinical-note.pdf")
    assert case["narrative_status"] == "failed"
    assert all(_v(case, k) == "" for k in ("presenting_symptoms", "medical_necessity", "risk_without_services"))


def test_handwritten_note_fills_the_form(recorded_claude):
    cid = _case()
    case = _upload(cid, "06-handwritten-clinical-note.pdf")
    assert recorded_claude == ["06-handwritten-clinical-note.pdf", "narrative"]
    assert case["documents"][0]["status"] == "extracted"
    assert _v(case, "member_name") == "O'Brien, James"
    assert _v(case, "member_dob") == "12/17/1983"
    assert _v(case, "member_id") == "ANT-XK7829014"
    assert _v(case, "payer") == "Anthem BCBS"
    assert _v(case, "icd10_codes") == "F33.1"
    assert _v(case, "provider_npi") == "1567890234"
    assert _v(case, "frequency") == "Weekly" and _v(case, "sessions_units") == "12"
    assert case["form"]["assessments"][0]["cells"] == {"tool": "PHQ-9", "score": "14", "date": "02/05/2026"}
    assert case["narrative_status"] == "done"
    assert case["form"]["fields"]["medical_necessity"]["source"] == "inferred"
    assert _v(case, "medical_necessity")

    pdf = client.get(f"/api/cases/{cid}/pdf")
    with pymupdf.open(stream=pdf.content, filetype="pdf") as doc:
        text = "".join(p.get_text() for p in doc)
        assert doc.page_count == 2
    assert "O'Brien, James" in text and "ANT-XK7829014" in text and "F33.1" in text


def test_referral_letter_fills_the_form():
    cid = _case()
    case = _upload(cid, "02-referral-letter.pdf")
    assert _v(case, "member_name") == "Dominguez, Elena R."
    assert _v(case, "icd10_codes") == "F33.1, F43.10"
    assert _v(case, "referring_name") == "Dr. Susan Okafor, MD"
    assert {"90792", "99214", "90837"} <= set(_v(case, "cpt_codes").split(", "))
    assert case["form"]["fields"]["member_id"]["evidence"][0]["quote"]

    assert _v(case, "tax_id") == ""
    assert any(i["field"] == "tax_id" and i["severity"] == "error" for i in case["issues"])


def test_documents_about_another_patient_are_excluded():
    cid = _case()
    case = _upload(
        cid,
        "02-referral-letter.pdf",
        "03-insurance-card.pdf",
        "04-lab-results.pdf",
        "05-patient-intake-form.pdf",
        "06-handwritten-clinical-note.pdf",
    )
    assert len(case["patient_groups"]) == 5
    included = [d["filename"] for d in case["documents"] if d["included"]]
    assert included == ["06-handwritten-clinical-note.pdf"]
    assert any("different patient" in i["message"] for i in case["issues"])

    other = next(g for g in case["patient_groups"] if "rodriguez" in g["key"])
    case = client.put(f"/api/cases/{cid}/primary-patient", json={"key": other["key"]}).json()
    assert _v(case, "member_name") == "Rodriguez, Carlos M."
    assert _v(case, "payer") == "Molina Healthcare of Texas"
    assert _v(case, "frequency") == "2x/week" and _v(case, "sessions_units") == "24"


def test_insurance_card_values_come_from_the_card_images():
    cid = _case()
    case = _upload(cid, "03-insurance-card.pdf")
    assert _v(case, "payer") == "UnitedHealthcare"
    assert _v(case, "member_id") == "UHC-84729103-05"
    assert _v(case, "group_number") == "742901"


def test_user_edits_survive_new_documents_and_clinic_settings():
    cid = _case()
    _upload(cid, "02-referral-letter.pdf")
    client.patch(f"/api/cases/{cid}/fields", json={"updates": {"payer_fax": "(800) 555-0100"}})
    client.put(
        "/api/clinic",
        json={
            "facility_name": "Sunrise Counseling Center",
            "tax_id": "74-1234567",
            "phone": "2105550890",
            "fax": "(210) 555-0891",
            "address": "100 Main St, San Antonio, TX 78205",
            "providers": [{"name": "Dr. Maya Patel, PsyD", "npi": "1234567893", "license_number": "TX-PSY-1"}],
            "default_provider_index": 0,
        },
    )
    case = client.get(f"/api/cases/{cid}").json()
    assert _v(case, "payer_fax") == "(800) 555-0100"
    assert _v(case, "provider_name") == "Dr. Maya Patel, PsyD"
    assert case["form"]["fields"]["provider_name"]["source"] == "clinic_profile"
    assert _v(case, "provider_phone") == "(210) 555-0890"
    assert _v(case, "signature") == ""
    case = client.post(f"/api/cases/{cid}/signature", json={"typed": True}).json()
    assert _v(case, "signature") == "Dr. Maya Patel, PsyD"
    client.put("/api/clinic", json={})


def test_long_text_goes_to_addendum():
    cid = _case()
    _upload(cid, "02-referral-letter.pdf")
    long_text = "Patient reports persistent low mood. " * 40
    client.patch(f"/api/cases/{cid}/fields", json={"updates": {"medical_necessity": long_text}})
    pdf = client.get(f"/api/cases/{cid}/pdf").content
    with pymupdf.open(stream=pdf, filetype="pdf") as doc:
        assert doc.page_count == 3
        assert "continued on addendum" in doc[1].get_text()
        assert "ADDENDUM" in doc[2].get_text()


def test_preview_highlights_quote():
    cid = _case()
    case = _upload(cid, "02-referral-letter.pdf")
    doc_id = case["documents"][0]["id"]
    r = client.get(
        f"/api/cases/{cid}/documents/{doc_id}/preview", params={"quote": "Electronically signed by Susan Okafor"}
    )
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"
    assert r.headers["x-page"] == "1"


@pytest.mark.parametrize("npi,ok", [("1234567893", True), ("1234567890", False), ("123", False)])
def test_npi_check_digit(npi, ok):
    assert npi_is_valid(npi) is ok


def test_name_and_identity_helpers():
    assert member_name_last_first(None, None, None, "Elena R. Dominguez") == "Dominguez, Elena R."
    assert member_name_last_first("Carlos", "M", "Rodriguez", None) == "Rodriguez, Carlos M."
    assert patient_key("Pt: James O'Brien", "12/17/83") == "o'brien|1983-12-17"
    assert patient_key("DAVID A. THOMPSON", None) == "thompson|?"


def test_signed_in_ant_profile_counts_as_credentials(tmp_path, monkeypatch):
    (tmp_path / "configs").mkdir()
    (tmp_path / "credentials").mkdir()
    (tmp_path / "configs" / "work.json").write_text('{"authentication": {"type": "user_oauth"}}')
    (tmp_path / "active_config").write_text("work")
    creds = tmp_path / "credentials" / "work.json"
    creds.write_text('{"type": "oauth_token", "access_token": "x", "refresh_token": "y", "expires_at": 4102444800}')
    creds.chmod(0o600)
    for var in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_PROFILE"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ANTHROPIC_CONFIG_DIR", str(tmp_path))
    assert credentials.require_credentials() == "signed-in profile 'work'"

    monkeypatch.setenv("ANTHROPIC_CONFIG_DIR", str(tmp_path / "nothing-here"))
    with pytest.raises(MissingCredentials):
        credentials.require_credentials()
