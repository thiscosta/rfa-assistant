from __future__ import annotations

import re
from datetime import date, datetime

_DATE_FORMATS = ("%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d", "%m-%d-%Y", "%m-%d-%y", "%B %d, %Y", "%b %d, %Y")


def parse_date(text: str | None) -> date | None:
    if not text:
        return None
    t = text.strip()
    m = re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b", t)
    if m:
        mo, d, y = (int(x) for x in m.groups())
        if y < 100:
            y += 2000 if y + 2000 <= date.today().year else 1900
        try:
            return date(y, mo, d)
        except ValueError:
            return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(t, fmt).date()
        except ValueError:
            continue
    return None


def fmt_date(d: date | None) -> str:
    return d.strftime("%m/%d/%Y") if d else ""


def normalize_date(text: str | None) -> str:
    d = parse_date(text)
    return fmt_date(d) if d else (text or "").strip()


def digits(text: str | None) -> str:
    return re.sub(r"\D", "", text or "")


def normalize_phone(text: str | None) -> str:
    d = digits(text)
    if len(d) == 11 and d.startswith("1"):
        d = d[1:]
    if len(d) == 10:
        return f"({d[:3]}) {d[3:6]}-{d[6:]}"
    return (text or "").strip()


def comparable(text: str | None) -> str:
    t = (text or "").lower()
    d = parse_date(t)
    if d and len(t) <= 12:
        return d.isoformat()
    return re.sub(r"[^a-z0-9]", "", t)


_TITLES = {"dr", "mr", "mrs", "ms", "miss", "md", "do", "phd", "psyd", "lcsw", "lpc", "np", "pa"}


def name_tokens(name: str | None) -> list[str]:
    raw = re.sub(r"[^A-Za-z,'\s-]", " ", name or "")
    if "," in raw:
        last, _, rest = raw.partition(",")
        raw = f"{rest} {last}"
    toks = [t.strip("'-").lower() for t in raw.split()]
    return [t for t in toks if t and t not in _TITLES]


def member_name_last_first(first: str | None, middle: str | None, last: str | None, full: str | None) -> str:
    if not (first and last) and full:
        toks = [t for t in re.split(r"\s+", re.sub(r",", " ", full).strip()) if t]
        if "," in full:
            last, _, rest = full.partition(",")
            parts = rest.split()
            first = parts[0] if parts else ""
            middle = parts[1] if len(parts) > 1 else middle
        elif len(toks) >= 2:
            first, last = toks[0], toks[-1]
            middle = toks[1] if len(toks) > 2 else middle
    if not (first and last):
        return (full or "").strip()
    mi = ""
    if middle:
        mi = f" {middle.strip().rstrip('.')[:1].upper()}."
    return f"{_title(last)}, {_title(first)}{mi}"


def _title(s: str) -> str:
    s = s.strip()
    return s if any(c.islower() for c in s) else s.title()


def patient_key(full_name: str | None, dob: str | None) -> str | None:
    d = parse_date(dob)
    toks = name_tokens(full_name)
    if not d and not toks:
        return None
    last = toks[-1] if toks else "?"
    return f"{last}|{d.isoformat() if d else '?'}"


def npi_is_valid(npi: str) -> bool:
    d = digits(npi)
    if len(d) != 10:
        return False
    payload = "80840" + d[:9]
    total = 0
    for i, ch in enumerate(reversed(payload)):
        n = int(ch)
        if i % 2 == 0:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    check = (10 - total % 10) % 10
    return check == int(d[9])


ICD10_RE = re.compile(r"\b([A-TV-Z][0-9][0-9A-Z](?:\.[0-9A-Z]{1,4})?)\b")


CPT_RE = re.compile(r"^(\d{4}[0-9A-Z]|[A-Z]\d{4})$")
