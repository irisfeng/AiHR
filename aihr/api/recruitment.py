from __future__ import annotations

from pathlib import Path
from typing import Any

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
def screen_job_applicant(job_applicant: str, save: int = 1) -> dict[str, Any]:
    if not frappe:
        raise RuntimeError("Frappe is required for screening Job Applicant records.")

    applicant = frappe.get_doc("Job Applicant", job_applicant)
    requirements = _get_job_requirements(applicant)
    preferred_skills = _get_requisition_field(applicant, "aihr_nice_to_have_skills")
    preferred_city = _get_job_opening_field(applicant, "location")

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


def _get_job_requirements(applicant) -> str:
    if not getattr(applicant, "job_title", None):
        return ""

    job_opening = frappe.get_doc("Job Opening", applicant.job_title)
    requirement_parts = [
        job_opening.description or "",
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
    applicant.save(ignore_permissions=True)
