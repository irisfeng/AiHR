from __future__ import annotations

import frappe
from frappe.utils import add_to_date, format_datetime, get_datetime, now_datetime

from aihr.api.recruitment import screen_job_applicant
from aihr.services.recruitment_ops import (
    build_feedback_summary,
    default_onboarding_activities,
    generate_requisition_agency_brief,
    get_feedback_next_action,
    get_interview_follow_up_action,
    get_onboarding_next_action,
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
    if not getattr(doc, "aihr_payroll_owner", None):
        doc.aihr_payroll_owner = getattr(doc, "aihr_onboarding_owner", None) or _default_owner(doc)
    if not getattr(doc, "aihr_payroll_handoff_status", None):
        doc.aihr_payroll_handoff_status = "Not Started"

    applicant = frappe.get_doc("Job Applicant", doc.job_applicant)
    if doc.status == "Accepted":
        applicant.aihr_ai_status = "Hired"
        applicant.status = "Accepted"
    elif doc.status == "Rejected":
        applicant.aihr_ai_status = "Rejected"
        applicant.status = "Rejected"
    else:
        applicant.aihr_ai_status = "Offer"
    applicant.aihr_next_action = get_offer_next_action(doc.status, doc.aihr_payroll_handoff_status)
    applicant.aihr_last_contact_at = now_datetime()
    applicant.save(ignore_permissions=True)


def sync_interview_feedback_defaults(doc, method=None) -> None:
    if not getattr(doc, "interview", None):
        return

    if not getattr(doc, "interviewer", None):
        interview_doc = frappe.get_doc("Interview", doc.interview)
        interviewers = [row.interviewer for row in getattr(interview_doc, "interview_details", []) if getattr(row, "interviewer", None)]
        doc.interviewer = interviewers[0] if interviewers else _default_owner(doc)

    if getattr(doc, "result", None):
        if not getattr(doc, "aihr_next_step_suggestion", None):
            doc.aihr_next_step_suggestion = get_feedback_next_action(doc.result)
        if not getattr(doc, "aihr_hiring_recommendation", None):
            doc.aihr_hiring_recommendation = "Yes" if doc.result == "Cleared" else "No"


def apply_interview_feedback_result(doc, method=None) -> None:
    if not getattr(doc, "interview", None) or not getattr(doc, "result", None):
        return

    average_rating = _calculate_average_rating(getattr(doc, "skill_assessment", []))
    interview_doc = frappe.get_doc("Interview", doc.interview)
    interview_doc.status = doc.result
    interview_doc.interview_summary = build_feedback_summary(
        interviewer=getattr(doc, "interviewer", ""),
        result=getattr(doc, "result", ""),
        average_rating=f"{average_rating:.1f} / 5" if average_rating else "待补充",
        feedback=getattr(doc, "feedback", ""),
        ratings=[
            f"{row.skill}: {row.rating or '--'} / 5"
            for row in getattr(doc, "skill_assessment", [])
            if getattr(row, "skill", None)
        ],
    )[:140]
    interview_doc.save(ignore_permissions=True)


def sync_employee_onboarding_defaults(doc, method=None) -> None:
    if not getattr(doc, "job_offer", None):
        return

    offer = frappe.get_doc("Job Offer", doc.job_offer)
    applicant = frappe.get_doc("Job Applicant", doc.job_applicant) if getattr(doc, "job_applicant", None) else None

    if not getattr(doc, "aihr_handoff_owner", None):
        doc.aihr_handoff_owner = getattr(offer, "aihr_onboarding_owner", None) or _default_owner(doc)
    if not getattr(doc, "aihr_employee_record", None) and getattr(doc, "employee", None):
        doc.aihr_employee_record = doc.employee
    if not getattr(doc, "aihr_preboarding_notes", None):
        doc.aihr_preboarding_notes = (
            f"{getattr(applicant, 'applicant_name', '候选人')} 的 Offer 已进入入职交接阶段。"
            f" {getattr(offer, 'aihr_compensation_notes', '') or '请确认资料、设备和薪酬建档信息。'}"
        ).strip()
    if not getattr(doc, "activities", None):
        for activity in default_onboarding_activities(doc.aihr_handoff_owner or _default_owner(doc)):
            doc.append("activities", activity)
    if not getattr(doc, "aihr_payroll_ready", None):
        doc.aihr_payroll_ready = 1 if getattr(offer, "aihr_payroll_handoff_status", "") in {"Ready", "Completed"} else 0
    if getattr(doc, "aihr_employee_record", None):
        doc.aihr_employee_creation_status = "Completed"
    elif getattr(doc, "aihr_payroll_ready", None):
        doc.aihr_employee_creation_status = "Ready"
    elif not getattr(doc, "aihr_employee_creation_status", None):
        doc.aihr_employee_creation_status = "Not Started"

    if applicant:
        applicant.aihr_next_action = get_onboarding_next_action(doc.boarding_status, bool(getattr(doc, "aihr_payroll_ready", 0)))
        applicant.aihr_last_contact_at = now_datetime()
        applicant.save(ignore_permissions=True)


def _auto_screen_job_applicant(doc, force: bool) -> None:
    if getattr(frappe.flags, "in_aihr_screening", False):
        return
    if getattr(frappe.flags, "aihr_skip_auto_screening", False):
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


def _calculate_average_rating(rows) -> float:
    ratings = [float(row.rating) for row in (rows or []) if getattr(row, "rating", None)]
    if not ratings:
        return 0
    return round(sum(ratings) / len(ratings), 1)
