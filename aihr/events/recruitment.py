from __future__ import annotations

import frappe

from aihr.api.recruitment import screen_job_applicant
from aihr.services.recruitment_ops import generate_requisition_agency_brief

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
