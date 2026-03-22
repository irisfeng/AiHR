from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from aihr.services.mineru_api import MinerUError, extract_pdf_text_with_mineru

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
    "linux",
    "docker",
    "kubernetes",
    "k8s",
    "nginx",
    "mysql",
    "redis",
    "ansible",
    "shell",
    "jenkins",
    "gitlab",
    "devops",
    "gitops",
    "argocd",
    "prometheus",
    "grafana",
    "zabbix",
    "tomcat",
    "ceph",
    "minio",
    "nfs",
    "技术支持",
    "实施",
    "交付",
    "运维",
    "容器化",
    "监控",
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
    "linux",
    "docker",
    "kubernetes",
    "k8s",
    "nginx",
    "mysql",
    "redis",
    "ansible",
    "shell",
    "jenkins",
    "gitlab",
    "devops",
    "gitops",
    "argocd",
    "prometheus",
    "grafana",
    "zabbix",
    "tomcat",
    "ceph",
    "minio",
    "nfs",
    "技术支持",
    "实施",
    "交付",
    "运维",
    "容器化",
    "监控",
}

EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
PHONE_RE = re.compile(r"(?:(?:\+?\d{1,3})?[\s-]?)?(?:\(?\d{2,4}\)?[\s-]?)?\d{3,4}[\s-]?\d{4}")
MOBILE_RE = re.compile(r"(?<!\d)(?:\+?86[-\s]?)?(1[3-9]\d{9})(?!\d)")
EN_YEARS_RE = re.compile(r"(\d{1,2})(?:\+)?\s*(?:years|yrs|year)\b", re.I)
ZH_YEARS_PATTERNS = [
    re.compile(r"(?:工作经验|工作年限|相关经验|从业经验)[:：\s]*(\d{1,2})(?:\+)?\s*年", re.I),
    re.compile(r"(\d{1,2})(?:\+)?\s*(?:年工作经验|年经验|年以上|年相关经验|年从业经验)", re.I),
    re.compile(r"(\d{1,2})(?:\+)?\s*年(?=[^\n]{0,12}(?:经验|工作|招聘|面试|入职|运维|实施|开发|测试|项目|运营|管理))", re.I),
]
LOCATION_PATTERNS = [
    re.compile(r"(?:location|city|based in)[:：\s]+([A-Za-z\u4e00-\u9fff][A-Za-z\u4e00-\u9fff\s,/-]{1,40})", re.I),
    re.compile(r"(?:现居|所在(?:地|城市)|工作地|期望城市|意向城市)[:：\s]+([A-Za-z\u4e00-\u9fff][A-Za-z\u4e00-\u9fff\s,/-]{1,40})", re.I),
]
NAME_LABEL_RE = re.compile(r"(?:姓\s*名|姓名)[:：\s]*([\u4e00-\u9fff·]{2,8})")
NAME_PREFIX_RE = re.compile(
    r"^([\u4e00-\u9fff·]{2,8})\s*(?:[-—_/|｜]|(?:应聘岗位|求职意向|简历|的简历).*)?$"
)
INVALID_NAME_PATTERNS = (
    "工作经历",
    "求职意向",
    "个人技能",
    "个人优势",
    "自我评价",
    "教育经历",
    "项目经历",
)
LOCATION_STOPWORDS = (
    "到岗时间",
    "个人技能",
    "个人优势",
    "工作经历",
    "求职意向",
    "邮箱",
    "电话",
)


def extract_text_from_file(file_path: str | Path, prefer_remote: bool = True) -> str:
    path = Path(file_path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        if prefer_remote:
            try:
                remote_text = extract_pdf_text_with_mineru(path)
            except MinerUError:
                remote_text = ""
            if remote_text.strip():
                return remote_text.strip()

        return extract_text_from_pdf_locally(path)

    if suffix == ".docx":
        return extract_text_from_docx(path)

    if suffix == ".doc":
        return extract_text_from_legacy_doc(path)

    return path.read_text(encoding="utf-8", errors="ignore").strip()


def extract_text_from_pdf_locally(file_path: str | Path) -> str:
    path = Path(file_path)
    try:
        from pypdf import PdfReader
    except Exception:
        return ""

    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages).strip()


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
    phones = extract_phones(normalized_text)
    years_of_experience = extract_years_of_experience(normalized_text)
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
    if cleaned.startswith("+86"):
        cleaned = cleaned[3:]
    elif cleaned.startswith("86") and len(cleaned) == 13:
        cleaned = cleaned[2:]
    return cleaned[:20]


def extract_phones(text: str) -> list[str]:
    mobile_numbers = sorted(set(match.group(1) for match in MOBILE_RE.finditer(text or "")))
    if mobile_numbers:
        return mobile_numbers

    candidates: list[str] = []
    for match in PHONE_RE.finditer(text or ""):
        cleaned = clean_phone(match.group(0))
        if not _looks_like_phone(cleaned):
            continue
        candidates.append(cleaned)
    return sorted(set(candidates))


def _looks_like_phone(value: str) -> bool:
    digits = value.lstrip("+")
    if not digits.isdigit():
        return False
    if len(digits) == 11 and digits.startswith("1"):
        return True
    if len(digits) == 8 and digits.startswith(("19", "20")):
        return False
    if len(digits) < 10 or len(digits) > 15:
        return False
    return True


def extract_years_of_experience(text: str) -> int:
    matches = [int(match.group(1)) for match in EN_YEARS_RE.finditer(text or "")]
    for pattern in ZH_YEARS_PATTERNS:
        matches.extend(int(match.group(1)) for match in pattern.finditer(text or ""))
    return max(matches, default=0)


def extract_city(text: str) -> str:
    for pattern in LOCATION_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        value = match.group(1).strip(" ,-")
        value = re.split(r"[|｜/]", value)[0].strip()
        for token in LOCATION_STOPWORDS:
            value = value.split(token)[0].strip()
        return value
    return ""


def infer_name(lines: list[str], emails: list[str], phones: list[str]) -> str:
    blocked_parts = set(emails + phones)
    for line in lines[:8]:
        explicit_match = NAME_LABEL_RE.search(line)
        if explicit_match:
            candidate = explicit_match.group(1).strip()
            if is_valid_name(candidate):
                return candidate

    for line in lines[:8]:
        if any(part and part in line for part in blocked_parts):
            continue
        if not line or line in INVALID_NAME_PATTERNS:
            continue
        if re.search(r"\d", line) and not NAME_LABEL_RE.search(line):
            continue
        if is_valid_name(line):
            return line.strip()
        prefix_match = NAME_PREFIX_RE.match(line.strip())
        if prefix_match:
            candidate = prefix_match.group(1).strip()
            if is_valid_name(candidate):
                return candidate
        words = line.split()
        if 1 < len(words) <= 4:
            return line.strip()
    return ""


def is_valid_name(value: str) -> bool:
    candidate = (value or "").strip()
    if not candidate:
        return False
    if candidate in INVALID_NAME_PATTERNS:
        return False
    if "：" in candidate or ":" in candidate:
        return False
    if len(candidate) > 8:
        return False
    if re.fullmatch(r"[\u4e00-\u9fff·]{2,8}", candidate):
        return True
    return False


def infer_name_from_file_name(file_name: str) -> str:
    stem = Path(file_name).stem
    stem = re.sub(r"\d{6,}", "", stem)
    stem = stem.replace("的简历", "").replace("简历", "")

    role_hint = re.match(
        r"^([\u4e00-\u9fff·]{2,4}?)(?=(?:实施|运维|项目|经理|顾问|工程师|开发|测试|产品|运营|技术|架构|售前|售后|$))",
        stem,
    )
    if role_hint:
        candidate = role_hint.group(1).strip()
        if is_valid_name(candidate):
            return candidate

    for separator in ("-", "—", "_", "｜", "|", "&", " "):
        head = stem.split(separator)[0].strip()
        if is_valid_name(head):
            return head

    pure_name = re.match(r"^([\u4e00-\u9fff·]{2,8})$", stem.strip())
    if pure_name:
        candidate = pure_name.group(1).strip()
        if is_valid_name(candidate):
            return candidate
    return ""


def detect_skills(text: str, lexicon: set[str]) -> list[str]:
    lowered = text.lower()
    found = []
    for skill in sorted(lexicon):
        if skill in lowered:
            found.append(skill)
    return found
