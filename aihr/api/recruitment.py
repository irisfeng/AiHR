from __future__ import annotations

from pathlib import Path
from typing import Any

from aihr.services.recruitment_ops import (
    generate_requisition_agency_brief,
    get_screening_next_action,
)
from aihr.services.resume_parser import extract_text_from_file, parse_resume_text
from aihr.services.screening import build_agency_brief, screen_candidate

try:
    import frappe
except Exception:  # pragma: no cover - keeps local tests independent from Frappe
    frappe = None


def _whitelist(fn):
    if frappe:
        return frappe.whitelist()(fn)
    return fn


@_whitelist
def preview_resume_screening(
    job_requirements: str,
    resume_text: str,
    preferred_skills: str | None = None,
    preferred_city: str | None = None,
) -> dict[str, Any]:
    parsed_resume = parse_resume_text(resume_text)
    result = screen_candidate(
        parsed_resume=parsed_resume,
        job_requirements=job_requirements,
        preferred_skills=preferred_skills or "",
        preferred_city=preferred_city or "",
    )
    return {
        "parsed_resume": parsed_resume,
        "screening": result,
    }


@_whitelist
def build_requisition_agency_brief(payload: dict[str, Any]) -> str:
    return build_agency_brief(payload)


@_whitelist
def get_job_applicant_snapshot(job_applicant: str) -> dict[str, Any]:
    if not frappe:
        raise RuntimeError("Frappe is required for fetching Job Applicant snapshots.")

    applicant = frappe.get_doc("Job Applicant", job_applicant)
    screening_name = frappe.db.get_value("AI Screening", {"job_applicant": applicant.name}, "name")
    screening = frappe.get_doc("AI Screening", screening_name) if screening_name else None
    job_opening = frappe.get_doc("Job Opening", applicant.job_title) if getattr(applicant, "job_title", None) else None
    requisition = (
        frappe.get_doc("Job Requisition", job_opening.job_requisition)
        if job_opening and getattr(job_opening, "job_requisition", None)
        else None
    )

    return {
        "job_applicant": {
            "name": applicant.name,
            "applicant_name": applicant.applicant_name,
            "email_id": applicant.email_id,
            "phone_number": applicant.phone_number,
            "status": applicant.status,
            "aihr_ai_status": getattr(applicant, "aihr_ai_status", ""),
            "aihr_match_score": getattr(applicant, "aihr_match_score", 0),
            "aihr_candidate_city": getattr(applicant, "aihr_candidate_city", ""),
            "aihr_years_experience": getattr(applicant, "aihr_years_experience", 0),
            "aihr_next_action": getattr(applicant, "aihr_next_action", ""),
        },
        "job_opening": {
            "name": job_opening.name,
            "job_title": job_opening.job_title,
        }
        if job_opening
        else None,
        "job_requisition": {
            "name": requisition.name,
            "aihr_work_city": getattr(requisition, "aihr_work_city", ""),
            "aihr_must_have_skills": getattr(requisition, "aihr_must_have_skills", ""),
            "aihr_nice_to_have_skills": getattr(requisition, "aihr_nice_to_have_skills", ""),
        }
        if requisition
        else None,
        "screening": {
            "name": screening.name,
            "status": screening.status,
            "overall_score": screening.overall_score,
            "matched_skills": _csv_to_list(screening.matched_skills),
            "missing_skills": _csv_to_list(screening.missing_skills),
            "ai_summary": screening.ai_summary,
            "strengths": _lines_to_list(screening.strengths),
            "risks": _lines_to_list(screening.risks),
            "suggested_questions": _lines_to_list(screening.suggested_questions),
        }
        if screening
        else None,
    }


@_whitelist
def get_job_opening_pipeline_summary(job_opening: str) -> dict[str, Any]:
    if not frappe:
        raise RuntimeError("Frappe is required for fetching Job Opening pipeline summaries.")

    applicants = frappe.get_all(
        "Job Applicant",
        filters={"job_title": job_opening},
        fields=[
            "name",
            "applicant_name",
            "status",
            "aihr_ai_status",
            "aihr_match_score",
            "aihr_next_action",
        ],
        order_by="aihr_match_score desc, modified desc",
    )

    status_counts: dict[str, int] = {}
    for applicant in applicants:
        status = applicant.get("aihr_ai_status") or applicant.get("status") or "Unknown"
        status_counts[status] = status_counts.get(status, 0) + 1

    return {
        "job_opening": job_opening,
        "total_applicants": len(applicants),
        "status_counts": status_counts,
        "top_candidates": applicants[:5],
    }


@_whitelist
def sync_job_requisition_agency_brief(job_requisition: str, save: int = 1) -> dict[str, Any]:
    if not frappe:
        raise RuntimeError("Frappe is required for syncing Job Requisition records.")

    requisition = frappe.get_doc("Job Requisition", job_requisition)
    brief = generate_requisition_agency_brief(requisition)

    if save:
        requisition.aihr_agency_brief = brief
        requisition.save(ignore_permissions=True)

    return {
        "job_requisition": requisition.name,
        "agency_brief": brief,
    }


@_whitelist
def sync_job_opening_agency_pack(job_opening: str, save: int = 1) -> dict[str, Any]:
    if not frappe:
        raise RuntimeError("Frappe is required for syncing Job Opening records.")

    opening = frappe.get_doc("Job Opening", job_opening)
    requisition = frappe.get_doc("Job Requisition", opening.job_requisition) if getattr(opening, "job_requisition", None) else None
    pack = generate_requisition_agency_brief(requisition) if requisition else opening.aihr_agency_pack or ""

    if requisition and getattr(requisition, "aihr_agency_brief", None):
        pack = requisition.aihr_agency_brief

    if save:
        opening.aihr_agency_pack = pack
        if not opening.aihr_next_action:
            opening.aihr_next_action = "收集并筛选候选人"
        opening.save(ignore_permissions=True)

    return {
        "job_opening": opening.name,
        "agency_pack": pack,
    }


@_whitelist
def screen_job_applicant(job_applicant: str, save: int = 1) -> dict[str, Any]:
    if not frappe:
        raise RuntimeError("Frappe is required for screening Job Applicant records.")

    applicant = frappe.get_doc("Job Applicant", job_applicant)
    requirements = _get_job_requirements(applicant)
    preferred_skills = _get_requisition_field(applicant, "aihr_nice_to_have_skills")
    preferred_city = _get_requisition_field(applicant, "aihr_work_city") or _get_job_opening_field(applicant, "location")

    resume_text = getattr(applicant, "aihr_resume_text", "") or ""
    if not resume_text and getattr(applicant, "resume_attachment", None):
        resume_text = _extract_resume_text_from_attachment(applicant.resume_attachment)

    parsed_resume = parse_resume_text(resume_text)
    screening = screen_candidate(
        parsed_resume=parsed_resume,
        job_requirements=requirements,
        preferred_skills=preferred_skills or "",
        preferred_city=preferred_city or "",
    )

    if save:
        _upsert_ai_screening(applicant, parsed_resume, screening)
        _update_applicant_summary(applicant, parsed_resume, screening, resume_text)

    return {
        "job_applicant": applicant.name,
        "parsed_resume": parsed_resume,
        "screening": screening,
    }


@_whitelist
def screen_job_opening_applicants(job_opening: str, save: int = 1) -> dict[str, Any]:
    if not frappe:
        raise RuntimeError("Frappe is required for screening Job Opening records.")

    applicants = frappe.get_all(
        "Job Applicant",
        filters={"job_title": job_opening},
        pluck="name",
    )
    screened = [screen_job_applicant(job_applicant=name, save=save) for name in applicants]

    return {
        "job_opening": job_opening,
        "screened_count": len(screened),
        "job_applicants": [item["job_applicant"] for item in screened],
    }


def _get_job_requirements(applicant) -> str:
    if not getattr(applicant, "job_title", None):
        return ""

    job_opening = frappe.get_doc("Job Opening", applicant.job_title)
    requirement_parts = [
        job_opening.description or "",
        _get_requisition_field(applicant, "description"),
        frappe.db.get_value(
            "Job Requisition",
            getattr(job_opening, "job_requisition", None),
            "aihr_must_have_skills",
        )
        or "",
        frappe.db.get_value(
            "Job Requisition",
            getattr(job_opening, "job_requisition", None),
            "aihr_nice_to_have_skills",
        )
        or "",
    ]
    return "\n".join(part for part in requirement_parts if part).strip()


def _get_job_opening_field(applicant, fieldname: str) -> str:
    if not getattr(applicant, "job_title", None):
        return ""
    return frappe.db.get_value("Job Opening", applicant.job_title, fieldname) or ""


def _get_requisition_field(applicant, fieldname: str) -> str:
    if not getattr(applicant, "job_title", None):
        return ""
    job_requisition = frappe.db.get_value("Job Opening", applicant.job_title, "job_requisition")
    if not job_requisition:
        return ""
    return frappe.db.get_value("Job Requisition", job_requisition, fieldname) or ""


def _extract_resume_text_from_attachment(file_url: str) -> str:
    if not file_url:
        return ""

    site_path = Path(frappe.get_site_path())
    relative_path = file_url.lstrip("/")
    file_path = site_path / relative_path
    if not file_path.exists():
        file_path = site_path / "public" / "files" / Path(file_url).name
    if not file_path.exists():
        file_path = site_path / "private" / "files" / Path(file_url).name
    if not file_path.exists():
        return ""
    return extract_text_from_file(file_path)


def _upsert_ai_screening(applicant, parsed_resume: dict[str, Any], screening: dict[str, Any]) -> None:
    existing = frappe.db.exists("AI Screening", {"job_applicant": applicant.name})
    doc = frappe.get_doc("AI Screening", existing) if existing else frappe.new_doc("AI Screening")

    doc.job_applicant = applicant.name
    doc.job_opening = applicant.job_title
    doc.status = screening["recommended_status"]
    doc.overall_score = screening["overall_score"]
    doc.matched_skills = ", ".join(screening["matched_skills"])
    doc.missing_skills = ", ".join(screening["missing_skills"])
    doc.ai_summary = screening["summary"]
    doc.strengths = "\n".join(screening["strengths"])
    doc.risks = "\n".join(screening["risks"])
    doc.suggested_questions = "\n".join(screening["suggested_questions"])
    doc.parsed_resume_json = frappe.as_json(parsed_resume, indent=2)
    doc.screening_payload_json = frappe.as_json(screening, indent=2)
    doc.save(ignore_permissions=True)


def _update_applicant_summary(applicant, parsed_resume: dict[str, Any], screening: dict[str, Any], resume_text: str) -> None:
    applicant.aihr_resume_text = resume_text
    applicant.aihr_ai_status = "Screened"
    applicant.aihr_match_score = screening["overall_score"]
    applicant.aihr_candidate_city = parsed_resume.get("city", "")
    applicant.aihr_years_experience = parsed_resume.get("years_of_experience", 0)
    applicant.aihr_next_action = get_screening_next_action(screening["recommended_status"])
    applicant.save(ignore_permissions=True)


def _csv_to_list(value: str | None) -> list[str]:
    return [item.strip() for item in (value or "").split(",") if item.strip()]


def _lines_to_list(value: str | None) -> list[str]:
    return [line.strip() for line in (value or "").splitlines() if line.strip()]
