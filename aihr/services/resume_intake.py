from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Iterable
from zipfile import ZipFile

from aihr.services.mineru_api import MinerUError, extract_pdf_texts_with_mineru, mineru_is_enabled
from aihr.services.resume_parser import extract_text_from_file, parse_resume_text

SUPPORTED_RESUME_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt"}


@dataclass
class ResumeArchiveItem:
    file_name: str
    file_extension: str
    content: bytes
    status: str
    reason: str = ""
    resume_text: str = ""
    parsed_resume: dict[str, Any] | None = None
    parser_engine: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["parsed_resume"] = self.parsed_resume or {}
        return payload


def extract_resume_archive(
    archive_path: str | Path,
    skill_lexicon: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    archive_file = Path(archive_path)
    if not archive_file.exists():
        raise FileNotFoundError(f"Resume archive does not exist: {archive_file}")

    if archive_file.suffix.lower() != ".zip":
        raise ValueError("Only ZIP resume bundles are supported.")

    extracted_items: list[ResumeArchiveItem] = []
    used_names: set[str] = set()
    pending_supported: list[tuple[ResumeArchiveItem, Path]] = []

    with TemporaryDirectory(prefix="aihr_resume_bundle_") as temp_dir:
        temp_root = Path(temp_dir)
        with ZipFile(archive_file) as bundle:
            for index, member in enumerate(bundle.infolist(), start=1):
                if member.is_dir():
                    continue

                original_name = Path(member.filename).name
                if not original_name or original_name.startswith(".") or original_name.startswith("__MACOSX"):
                    continue

                suffix = Path(original_name).suffix.lower()
                safe_name = _dedupe_name(original_name, used_names, index)
                member_bytes = bundle.read(member)

                if suffix not in SUPPORTED_RESUME_EXTENSIONS:
                    extracted_items.append(
                        ResumeArchiveItem(
                            file_name=safe_name,
                            file_extension=suffix or "",
                            content=member_bytes,
                            status="Unsupported",
                            reason="仅支持 PDF、DOCX、DOC、TXT 格式的简历文件。",
                        )
                    )
                    continue

                temp_path = temp_root / safe_name
                temp_path.write_bytes(member_bytes)
                pending_supported.append(
                    (
                        ResumeArchiveItem(
                            file_name=safe_name,
                            file_extension=suffix,
                            content=member_bytes,
                            status="Pending",
                        ),
                        temp_path,
                    )
                )

        mineru_results: dict[str, Any] = {}
        if mineru_is_enabled():
            pdf_paths = [temp_path for item, temp_path in pending_supported if item.file_extension == ".pdf"]
            if pdf_paths:
                try:
                    mineru_results = extract_pdf_texts_with_mineru(pdf_paths)
                except MinerUError:
                    mineru_results = {}

        for item, temp_path in pending_supported:
            resume_text = ""
            parser_engine = ""

            if item.file_extension == ".pdf":
                mineru_result = mineru_results.get(str(temp_path))
                if mineru_result and mineru_result.text.strip():
                    resume_text = mineru_result.text
                    parser_engine = "MinerU API"
                else:
                    resume_text = extract_text_from_file(temp_path, prefer_remote=False)
                    parser_engine = "Local PDF"
            else:
                resume_text = extract_text_from_file(temp_path)
                parser_engine = temp_path.suffix.upper().lstrip(".")

            if not resume_text.strip():
                item.status = "Failed"
                item.reason = "文件未能提取出可用文本，请人工补充或转成可复制文本。"
                item.parser_engine = parser_engine
                extracted_items.append(item)
                continue

            item.status = "Parsed"
            item.resume_text = resume_text
            item.parsed_resume = parse_resume_text(resume_text, skill_lexicon=skill_lexicon)
            item.parser_engine = parser_engine
            extracted_items.append(item)

    return [item.to_dict() for item in extracted_items]


def summarize_archive_results(items: list[dict[str, Any]]) -> dict[str, int]:
    summary = {
        "total_files": len(items),
        "parsed_count": 0,
        "unsupported_count": 0,
        "failed_count": 0,
    }
    for item in items:
        status = (item.get("status") or "").strip()
        if status == "Parsed":
            summary["parsed_count"] += 1
        elif status == "Unsupported":
            summary["unsupported_count"] += 1
        elif status == "Failed":
            summary["failed_count"] += 1
    return summary


def _dedupe_name(file_name: str, used_names: set[str], index: int) -> str:
    candidate = file_name.strip().replace("/", "_").replace("\\", "_")
    if candidate not in used_names:
        used_names.add(candidate)
        return candidate

    stem = Path(candidate).stem or f"resume_{index}"
    suffix = Path(candidate).suffix
    serial = 2
    while True:
        next_candidate = f"{stem}_{serial}{suffix}"
        if next_candidate not in used_names:
            used_names.add(next_candidate)
            return next_candidate
        serial += 1
