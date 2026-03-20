from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

DEFAULT_SKILL_LEXICON = {
    "python",
    "java",
    "javascript",
    "typescript",
    "sql",
    "excel",
    "powerpoint",
    "recruiting",
    "sourcing",
    "interviewing",
    "payroll",
    "onboarding",
    "employee relations",
    "labor law",
    "compensation",
    "talent acquisition",
    "project management",
    "communication",
    "sales",
    "customer success",
    "product management",
    "operations",
    "data analysis",
    "figma",
}

EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
PHONE_RE = re.compile(r"(?:(?:\+?\d{1,3})?[\s-]?)?(?:\(?\d{2,4}\)?[\s-]?)?\d{3,4}[\s-]?\d{4}")
YEARS_RE = re.compile(r"(\d{1,2})(?:\+)?\s*(?:years|yrs|year)\b", re.I)
LOCATION_RE = re.compile(r"(?:location|city|based in)[:\s]+([A-Za-z][A-Za-z\s,/-]{1,40})", re.I)


def extract_text_from_file(file_path: str | Path) -> str:
    path = Path(file_path)
    if path.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader
        except Exception:
            return ""

        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages).strip()

    return path.read_text(encoding="utf-8", errors="ignore").strip()


def parse_resume_text(text: str, skill_lexicon: Iterable[str] | None = None) -> dict[str, object]:
    normalized_text = normalize_whitespace(text)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    lexicon = {skill.lower() for skill in (skill_lexicon or DEFAULT_SKILL_LEXICON)}

    emails = sorted(set(match.group(0) for match in EMAIL_RE.finditer(normalized_text)))
    phones = sorted(set(clean_phone(match.group(0)) for match in PHONE_RE.finditer(normalized_text)))
    years_of_experience = max((int(match.group(1)) for match in YEARS_RE.finditer(normalized_text)), default=0)
    city = extract_city(normalized_text)
    skills = detect_skills(normalized_text, lexicon)
    name = infer_name(lines, emails, phones)

    return {
        "name": name,
        "emails": emails,
        "phones": phones,
        "city": city,
        "years_of_experience": years_of_experience,
        "skills": skills,
        "raw_text_length": len(normalized_text),
    }


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def clean_phone(phone: str) -> str:
    cleaned = re.sub(r"[^\d+]", "", phone)
    return cleaned[:20]


def extract_city(text: str) -> str:
    match = LOCATION_RE.search(text)
    if not match:
        return ""
    return match.group(1).strip(" ,-")


def infer_name(lines: list[str], emails: list[str], phones: list[str]) -> str:
    blocked_parts = set(emails + phones)
    for line in lines[:5]:
        if any(part and part in line for part in blocked_parts):
            continue
        if re.search(r"\d", line):
            continue
        words = line.split()
        if 1 < len(words) <= 4:
            return line.strip()
    return ""


def detect_skills(text: str, lexicon: set[str]) -> list[str]:
    lowered = text.lower()
    found = []
    for skill in sorted(lexicon):
        if skill in lowered:
            found.append(skill)
    return found

