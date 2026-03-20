from __future__ import annotations

import frappe
from frappe.utils import add_to_date, format_datetime, get_datetime, now_datetime

from aihr.api.recruitment import screen_job_applicant
from aihr.services.recruitment_ops import (
    generate_requisition_agency_brief,
    get_interview_follow_up_action,
    get_offer_next_action,
)

REQUISITION_BRIEF_FIELDS = (
    "designation",
    "department",
    "description",
    "reason_for_requesting",
    "aihr_work_city",
    "aihr_work_mode",
    "aihr_work_schedule",
    "aihr_salary_currency",
    "aihr_salary_min",
    "aihr_salary_max",
    "aihr_must_have_skills",
    "aihr_nice_to_have_skills",
)

APPLICANT_AUTOSCREEN_FIELDS = ("aihr_resume_text", "resume_attachment", "job_title")


def sync_job_requisition_brief(doc, method=None) -> None:
    if not any(getattr(doc, fieldname, None) for fieldname in REQUISITION_BRIEF_FIELDS):
        return

    doc.aihr_agency_brief = generate_requisition_agency_brief(doc)


def sync_job_opening_pack(doc, method=None) -> None:
    if not getattr(doc, "job_requisition", None):
        return

    requisition = frappe.get_doc("Job Requisition", doc.job_requisition)
    doc.aihr_agency_pack = requisition.aihr_agency_brief or generate_requisition_agency_brief(requisition)

    if not getattr(doc, "aihr_next_action", None):
        doc.aihr_next_action = "收集并筛选候选人"


def auto_screen_job_applicant_after_insert(doc, method=None) -> None:
    _auto_screen_job_applicant(doc, force=True)


def auto_screen_job_applicant_on_update(doc, method=None) -> None:
    _auto_screen_job_applicant(doc, force=False)


def sync_interview_ops(doc, method=None) -> None:
    if not getattr(doc, "job_applicant", None):
        return

    if not getattr(doc, "aihr_follow_up_owner", None):
        doc.aihr_follow_up_owner = _default_owner(doc)
    if not getattr(doc, "aihr_feedback_due_at", None) and getattr(doc, "scheduled_on", None):
        doc.aihr_feedback_due_at = get_datetime(f"{add_to_date(doc.scheduled_on, days=1)} 12:00:00")

    applicant = frappe.get_doc("Job Applicant", doc.job_applicant)
    applicant.aihr_ai_status = "Rejected" if doc.status == "Rejected" else "Interview"
    applicant.aihr_next_action = get_interview_follow_up_action(
        doc.status,
        format_datetime(doc.aihr_feedback_due_at) if getattr(doc, "aihr_feedback_due_at", None) else "",
    )
    applicant.aihr_next_action_at = getattr(doc, "aihr_feedback_due_at", None) or None
    applicant.aihr_last_contact_at = now_datetime()
    applicant.save(ignore_permissions=True)


def sync_job_offer_ops(doc, method=None) -> None:
    if not getattr(doc, "job_applicant", None):
        return

    if not getattr(doc, "aihr_onboarding_owner", None):
        doc.aihr_onboarding_owner = _default_owner(doc)
    if not getattr(doc, "aihr_payroll_handoff_status", None):
        doc.aihr_payroll_handoff_status = "Not Started"

    applicant = frappe.get_doc("Job Applicant", doc.job_applicant)
    if doc.status == "Accepted":
        applicant.aihr_ai_status = "Hired"
    elif doc.status == "Rejected":
        applicant.aihr_ai_status = "Rejected"
    else:
        applicant.aihr_ai_status = "Offer"
    applicant.aihr_next_action = get_offer_next_action(doc.status, doc.aihr_payroll_handoff_status)
    applicant.aihr_last_contact_at = now_datetime()
    applicant.save(ignore_permissions=True)


def _auto_screen_job_applicant(doc, force: bool) -> None:
    if getattr(frappe.flags, "in_aihr_screening", False):
        return

    if not getattr(doc, "job_title", None):
        return

    has_resume_source = bool(getattr(doc, "aihr_resume_text", None) or getattr(doc, "resume_attachment", None))
    if not has_resume_source:
        return

    if not force and not any(doc.has_value_changed(fieldname) for fieldname in APPLICANT_AUTOSCREEN_FIELDS):
        return

    try:
        frappe.flags.in_aihr_screening = True
        screen_job_applicant(doc.name, save=1)
    except Exception:
        frappe.log_error(
            title=f"AIHR auto screening failed for {doc.name}",
            message=frappe.get_traceback(),
        )
    finally:
        frappe.flags.in_aihr_screening = False


def _default_owner(doc) -> str:
    session_user = getattr(frappe.session, "user", None)
    if session_user and session_user != "Guest":
        return session_user
    return getattr(doc, "owner", None) or "Administrator"
