from __future__ import annotations

from typing import Any


def ensure_custom_fields() -> None:
    import frappe
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

    create_custom_fields(get_custom_fields(), ignore_validate=True)
    frappe.clear_cache()


def get_custom_fields() -> dict[str, list[dict[str, Any]]]:
    return {
        "Job Requisition": [
            {
                "fieldname": "aihr_hiring_profile_section",
                "fieldtype": "Section Break",
                "label": "AIHR Hiring Profile",
                "insert_after": "reason_for_requesting",
            },
            {
                "fieldname": "aihr_priority",
                "fieldtype": "Select",
                "label": "Hiring Priority",
                "options": "Critical\nHigh\nNormal",
                "insert_after": "aihr_hiring_profile_section",
            },
            {
                "fieldname": "aihr_work_mode",
                "fieldtype": "Select",
                "label": "Work Mode",
                "options": "Onsite\nHybrid\nRemote",
                "insert_after": "aihr_priority",
            },
            {
                "fieldname": "aihr_column_break_profile",
                "fieldtype": "Column Break",
                "insert_after": "aihr_work_mode",
            },
            {
                "fieldname": "aihr_work_city",
                "fieldtype": "Data",
                "label": "Work City",
                "insert_after": "aihr_column_break_profile",
            },
            {
                "fieldname": "aihr_work_schedule",
                "fieldtype": "Data",
                "label": "Work Schedule",
                "insert_after": "aihr_work_city",
            },
            {
                "fieldname": "aihr_salary_currency",
                "fieldtype": "Link",
                "label": "Salary Currency",
                "options": "Currency",
                "insert_after": "aihr_work_schedule",
            },
            {
                "fieldname": "aihr_salary_min",
                "fieldtype": "Currency",
                "label": "Salary Min",
                "options": "aihr_salary_currency",
                "insert_after": "aihr_salary_currency",
            },
            {
                "fieldname": "aihr_salary_max",
                "fieldtype": "Currency",
                "label": "Salary Max",
                "options": "aihr_salary_currency",
                "insert_after": "aihr_salary_min",
            },
            {
                "fieldname": "aihr_must_have_skills",
                "fieldtype": "Small Text",
                "label": "Must Have Skills",
                "insert_after": "aihr_salary_max",
            },
            {
                "fieldname": "aihr_nice_to_have_skills",
                "fieldtype": "Small Text",
                "label": "Nice To Have Skills",
                "insert_after": "aihr_must_have_skills",
            },
            {
                "fieldname": "aihr_agency_brief",
                "fieldtype": "Text Editor",
                "label": "Agency Brief",
                "insert_after": "aihr_nice_to_have_skills",
            },
        ],
        "Job Opening": [
            {
                "fieldname": "aihr_recruitment_ops_section",
                "fieldtype": "Section Break",
                "label": "AIHR Recruitment Ops",
                "insert_after": "publish_salary_range",
            },
            {
                "fieldname": "aihr_posting_owner",
                "fieldtype": "Link",
                "label": "Posting Owner",
                "options": "User",
                "insert_after": "aihr_recruitment_ops_section",
            },
            {
                "fieldname": "aihr_channel_mix",
                "fieldtype": "Small Text",
                "label": "Channel Mix",
                "insert_after": "aihr_posting_owner",
            },
            {
                "fieldname": "aihr_daily_sync_time",
                "fieldtype": "Time",
                "label": "Daily Sync Time",
                "insert_after": "aihr_channel_mix",
            },
            {
                "fieldname": "aihr_next_action",
                "fieldtype": "Data",
                "label": "Next Action",
                "insert_after": "aihr_daily_sync_time",
            },
            {
                "fieldname": "aihr_agency_pack",
                "fieldtype": "Text Editor",
                "label": "Agency Pack",
                "insert_after": "aihr_next_action",
            },
        ],
        "Job Applicant": [
            {
                "fieldname": "aihr_candidate_ops_section",
                "fieldtype": "Section Break",
                "label": "AIHR Candidate Ops",
                "insert_after": "resume_link",
            },
            {
                "fieldname": "aihr_resume_text",
                "fieldtype": "Long Text",
                "label": "Resume Text",
                "insert_after": "aihr_candidate_ops_section",
            },
            {
                "fieldname": "aihr_ai_status",
                "fieldtype": "Select",
                "label": "AIHR Status",
                "options": "Not Screened\nScreened\nManager Review\nInterview\nRejected\nOffer\nHired",
                "insert_after": "aihr_resume_text",
            },
            {
                "fieldname": "aihr_match_score",
                "fieldtype": "Percent",
                "label": "Match Score",
                "insert_after": "aihr_ai_status",
            },
            {
                "fieldname": "aihr_candidate_city",
                "fieldtype": "Data",
                "label": "Candidate City",
                "insert_after": "aihr_match_score",
            },
            {
                "fieldname": "aihr_years_experience",
                "fieldtype": "Float",
                "label": "Years Of Experience",
                "insert_after": "aihr_candidate_city",
            },
            {
                "fieldname": "aihr_last_contact_at",
                "fieldtype": "Datetime",
                "label": "Last Contact At",
                "insert_after": "aihr_years_experience",
            },
            {
                "fieldname": "aihr_next_action",
                "fieldtype": "Data",
                "label": "Next Action",
                "insert_after": "aihr_last_contact_at",
            },
            {
                "fieldname": "aihr_next_action_at",
                "fieldtype": "Datetime",
                "label": "Next Action At",
                "insert_after": "aihr_next_action",
            },
        ],
        "Interview": [
            {
                "fieldname": "aihr_interview_ops_section",
                "fieldtype": "Section Break",
                "label": "AIHR Interview Ops",
                "insert_after": "interview_summary",
            },
            {
                "fieldname": "aihr_interview_mode",
                "fieldtype": "Select",
                "label": "Interview Mode",
                "options": "Phone\nVideo\nOnsite",
                "insert_after": "aihr_interview_ops_section",
            },
            {
                "fieldname": "aihr_follow_up_owner",
                "fieldtype": "Link",
                "label": "Follow Up Owner",
                "options": "User",
                "insert_after": "aihr_interview_mode",
            },
            {
                "fieldname": "aihr_feedback_due_at",
                "fieldtype": "Datetime",
                "label": "Feedback Due At",
                "insert_after": "aihr_follow_up_owner",
            },
            {
                "fieldname": "aihr_interviewer_pack",
                "fieldtype": "Text Editor",
                "label": "Interviewer Pack",
                "insert_after": "aihr_feedback_due_at",
            },
        ],
        "Job Offer": [
            {
                "fieldname": "aihr_offer_ops_section",
                "fieldtype": "Section Break",
                "label": "AIHR Offer Ops",
                "insert_after": "terms",
            },
            {
                "fieldname": "aihr_onboarding_owner",
                "fieldtype": "Link",
                "label": "Onboarding Owner",
                "options": "User",
                "insert_after": "aihr_offer_ops_section",
            },
            {
                "fieldname": "aihr_payroll_handoff_status",
                "fieldtype": "Select",
                "label": "Payroll Handoff Status",
                "options": "Not Started\nReady\nCompleted",
                "insert_after": "aihr_onboarding_owner",
            },
            {
                "fieldname": "aihr_compensation_notes",
                "fieldtype": "Small Text",
                "label": "Compensation Notes",
                "insert_after": "aihr_payroll_handoff_status",
            },
        ],
    }

