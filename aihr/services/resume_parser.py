from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET
from zipfile import ZipFile

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
    "招聘",
    "招聘运营",
    "人才获取",
    "人才招聘",
    "入职",
    "薪酬",
    "薪资",
    "员工关系",
    "劳动法",
    "面试",
    "组织协同",
    "数据分析",
    "项目管理",
    "沟通",
    "excel",
}

EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
PHONE_RE = re.compile(r"(?:(?:\+?\d{1,3})?[\s-]?)?(?:\(?\d{2,4}\)?[\s-]?)?\d{3,4}[\s-]?\d{4}")
YEARS_RE = re.compile(
    r"(\d{1,2})(?:\+)?\s*(?:years|yrs|year)\b|(\d{1,2})(?:\+)?\s*(?:年经验|年以上|年工作经验|年)",
    re.I,
)
LOCATION_RE = re.compile(
    r"(?:location|city|based in|现居|所在(?:地|城市)|工作地)[:：\s]+([A-Za-z\u4e00-\u9fff][A-Za-z\u4e00-\u9fff\s,/-]{1,40})",
    re.I,
)


def extract_text_from_file(file_path: str | Path) -> str:
    path = Path(file_path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
        except Exception:
            return ""

        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages).strip()

    if suffix == ".docx":
        return extract_text_from_docx(path)

    if suffix == ".doc":
        return extract_text_from_legacy_doc(path)

    return path.read_text(encoding="utf-8", errors="ignore").strip()


def extract_text_from_docx(file_path: str | Path) -> str:
    path = Path(file_path)
    if not path.exists():
        return ""

    try:
        with ZipFile(path) as archive:
            xml_bytes = archive.read("word/document.xml")
    except Exception:
        return ""

    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return ""

    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs: list[str] = []
    for paragraph in root.findall(".//w:p", namespace):
        texts = [node.text or "" for node in paragraph.findall(".//w:t", namespace)]
        content = "".join(texts).strip()
        if content:
            paragraphs.append(content)
    return "\n".join(paragraphs).strip()


def extract_text_from_legacy_doc(file_path: str | Path) -> str:
    antiword = shutil.which("antiword")
    if not antiword:
        return ""

    try:
        result = subprocess.run(
            [antiword, str(file_path)],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
    except Exception:
        return ""

    return (result.stdout or "").strip()


def parse_resume_text(text: str, skill_lexicon: Iterable[str] | None = None) -> dict[str, object]:
    normalized_text = normalize_whitespace(text)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    lexicon = {skill.lower() for skill in (skill_lexicon or DEFAULT_SKILL_LEXICON)}

    emails = sorted(set(match.group(0) for match in EMAIL_RE.finditer(normalized_text)))
    phones = sorted(set(clean_phone(match.group(0)) for match in PHONE_RE.finditer(normalized_text)))
    years_of_experience = max(
        (
            int(match.group(1) or match.group(2))
            for match in YEARS_RE.finditer(normalized_text)
            if match.group(1) or match.group(2)
        ),
        default=0,
    )
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
        if re.fullmatch(r"[\u4e00-\u9fff]{2,6}", line.strip()):
            return line.strip()
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
