from __future__ import annotations

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.removeprefix("export ").strip()
        os.environ.setdefault(key, value.strip().strip("'\""))


_load_dotenv(BACKEND_DIR / ".env")


DATA_DIR = Path(os.environ.get("RFA_DATA_DIR", BACKEND_DIR / "data"))


TEMPLATE_PDF = BACKEND_DIR / "templates" / "request-for-approval-of-services.pdf"


CLAUDE_MODEL = os.environ.get("RFA_CLAUDE_MODEL", "claude-opus-5-5")


CORS_ORIGINS = os.environ.get("RFA_CORS_ORIGINS", "http://localhost:3100,http://127.0.0.1:3100").split(",")


MAX_UPLOAD_BYTES = 25 * 1024 * 1024


ACCEPTED_TYPES = {"application/pdf", "image/png", "image/jpeg"}
