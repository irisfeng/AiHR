from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aihr.services.resume_intake import extract_resume_archive, summarize_archive_results
from aihr.services.screening import screen_candidate


def build_docx_bytes(paragraphs: list[str]) -> bytes:
    xml = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">',
        "  <w:body>",
    ]
    for paragraph in paragraphs:
        content = (
            paragraph.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        xml.append(f"    <w:p><w:r><w:t>{content}</w:t></w:r></w:p>")
    xml += ["  </w:body>", "</w:document>"]

    with tempfile.TemporaryDirectory() as temp_dir:
        docx_path = Path(temp_dir) / "resume.docx"
        with ZipFile(docx_path, "w") as archive:
            archive.writestr("[Content_Types].xml", "")
            archive.writestr("word/document.xml", "\n".join(xml))
        return docx_path.read_bytes()


def build_chinese_zip_bundle(target_path: Path) -> None:
    with ZipFile(target_path, "w") as bundle:
        bundle.writestr(
            "王小雨_招聘经理.docx",
            build_docx_bytes(
                [
                    "王小雨",
                    "wangxiaoyu@demo.com",
                    "13800138011",
                    "现居：上海",
                    "6年招聘、面试、入职和数据分析经验。",
                    "曾支持互联网公司年度批量招聘与校园招聘项目。",
                ]
            ),
        )
        bundle.writestr(
            "李娜_招聘运营.txt",
            "\n".join(
                [
                    "李娜",
                    "lina@demo.com",
                    "13800138012",
                    "现居：杭州",
                    "4年招聘运营、面试协调、入职办理经验，熟悉招聘、面试、入职、沟通。",
                    "曾负责招聘渠道管理和周报分析。",
                ]
            ),
        )
        bundle.writestr("供应商说明.xlsx", b"binary")


def main() -> None:
    job_requirements = (
        "负责中文招聘需求梳理、简历初筛、面试协同与候选人推进。"
        "优先考虑具备招聘、面试、入职和数据分析经验的候选人。需要 4 年以上相关经验。"
    )
    preferred_skills = "薪酬, 员工关系, 沟通"
    preferred_city = "上海"

    with tempfile.TemporaryDirectory(prefix="aihr_cn_materials_") as temp_dir:
        archive_path = Path(temp_dir) / "中文简历包.zip"
        build_chinese_zip_bundle(archive_path)

        items = extract_resume_archive(archive_path)
        summary = summarize_archive_results(items)

        report: dict[str, object] = {
            "archive": str(archive_path),
            "summary": summary,
            "screenings": [],
        }
        for item in items:
            payload = {
                "file_name": item["file_name"],
                "status": item["status"],
                "reason": item.get("reason", ""),
            }
            if item["status"] == "Parsed":
                screening = screen_candidate(
                    parsed_resume=item["parsed_resume"],
                    job_requirements=job_requirements,
                    preferred_skills=preferred_skills,
                    preferred_city=preferred_city,
                )
                payload["parsed_resume"] = item["parsed_resume"]
                payload["screening"] = screening
            report["screenings"].append(payload)

        print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
