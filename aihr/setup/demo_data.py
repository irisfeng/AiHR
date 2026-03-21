from __future__ import annotations

from typing import Any

import frappe
from frappe.utils import add_to_date, get_datetime, now_datetime

from aihr.services.recruitment_ops import build_interviewer_pack, default_onboarding_activities
from aihr.services.resume_parser import parse_resume_text
from aihr.services.screening import build_agency_brief, screen_candidate


def seed_demo_recruitment_data(company: str) -> dict[str, str]:
    company_doc = _ensure_company(company)
    department = _ensure_department("People", company_doc.name)
    designation = _ensure_designation("HRBP")
    requester = _ensure_requester(company_doc.name, department.name, designation.name)

    requisition = _get_or_create_requisition(
        company=company_doc.name,
        department=department.name,
        designation=designation.name,
        requested_by=requester.name,
    )
    job_opening = _get_or_create_job_opening(
        company=company_doc.name,
        department=department.name,
        designation=designation.name,
        requisition=requisition.name,
    )

    applicant_docs = []
    for sample in _candidate_samples():
        applicant = _get_or_create_job_applicant(job_opening.name, sample)
        _screen_applicant(applicant, requisition, job_opening)
        applicant_docs.append(applicant)

    interview_round = _ensure_interview_round(designation.name)
    interview = _get_or_create_interview(job_opening, applicant_docs[0], interview_round, requester.user_id)
    interview_feedback = _get_or_create_interview_feedback(interview, requester.user_id)
    job_offer = _get_or_create_job_offer(company_doc.name, designation.name, applicant_docs[-1], job_opening, requester.user_id)
    employee_onboarding = _get_or_create_employee_onboarding(job_offer, applicant_docs[-1], job_opening, requester.user_id)

    return {
        "company": company_doc.name,
        "job_requisition": requisition.name,
        "job_opening": job_opening.name,
        "job_applicants": ", ".join(applicant.name for applicant in applicant_docs),
        "interview": interview.name,
        "interview_feedback": interview_feedback.name,
        "job_offer": job_offer.name,
        "employee_onboarding": employee_onboarding.name,
    }


def _ensure_company(name: str):
    existing = frappe.db.exists("Company", name)
    if existing:
        return frappe.get_doc("Company", existing)

    first_company = frappe.db.get_value("Company", {}, "name")
    if first_company:
        return frappe.get_doc("Company", first_company)

    from frappe.desk.page.setup_wizard.setup_wizard import setup_complete

    year = now_datetime().year
    company_abbr = "".join(part[0] for part in name.split()[:3]).upper() or "AIH"

    setup_complete(
        {
            "currency": "CNY",
            "full_name": "AIHR Demo Admin",
            "company_name": name,
            "timezone": "Asia/Shanghai",
            "company_abbr": company_abbr[:5],
            "industry": "Technology",
            "country": "China",
            "fy_start_date": f"{year}-01-01",
            "fy_end_date": f"{year}-12-31",
            "language": "english",
            "company_tagline": "AIHR MVP Demo",
            "email": "admin@aihr.local",
            "password": "AIHRAdmin!2026",
            "chart_of_accounts": "Standard",
        }
    )
    frappe.db.commit()
    return frappe.get_doc("Company", name)


def _ensure_department(name: str, company: str):
    existing = frappe.db.get_value("Department", {"department_name": name, "company": company}, "name")
    if existing:
        return frappe.get_doc("Department", existing)

    doc = frappe.new_doc("Department")
    doc.department_name = name
    doc.company = company
    doc.save(ignore_permissions=True)
    return doc


def _ensure_designation(name: str):
    existing = frappe.db.exists("Designation", name)
    if existing:
        return frappe.get_doc("Designation", existing)

    doc = frappe.new_doc("Designation")
    doc.designation_name = name
    doc.save(ignore_permissions=True)
    return doc


def _ensure_requester(company: str, department: str, designation: str):
    user_id = "manager.demo@aihr.local"
    employee_name = frappe.db.get_value("Employee", {"user_id": user_id})
    if employee_name:
        return frappe.get_doc("Employee", employee_name)

    if not frappe.db.exists("User", user_id):
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": user_id,
                "first_name": "Hiring",
                "last_name": "Manager",
                "new_password": "AIHRDemo!2026",
                "send_welcome_email": 0,
            }
        )
        user.insert(ignore_permissions=True)

    employee = frappe.get_doc(
        {
            "doctype": "Employee",
            "naming_series": "HR-EMP-",
            "first_name": "Hiring",
            "last_name": "Manager",
            "company": company,
            "department": department,
            "designation": designation,
            "user_id": user_id,
            "date_of_birth": "1990-05-08",
            "date_of_joining": f"{now_datetime().date()}",
            "gender": "Female",
            "company_email": user_id,
            "prefered_contact_email": "Company Email",
            "prefered_email": user_id,
            "status": "Active",
        }
    )
    employee.insert(ignore_permissions=True)
    return employee


def _get_or_create_requisition(company: str, department: str, designation: str, requested_by: str):
    existing = frappe.db.exists(
        "Job Requisition",
        {"company": company, "designation": designation, "department": department},
    )
    if existing:
        return frappe.get_doc("Job Requisition", existing)

    doc = frappe.new_doc("Job Requisition")
    doc.designation = designation
    doc.department = department
    doc.requested_by = requested_by
    doc.no_of_positions = 1
    doc.expected_compensation = 30000
    doc.company = company
    doc.status = "Open & Approved"
    doc.description = "负责招聘、入职、组织协同，支持 AIHR 系统试运行。"
    doc.reason_for_requesting = "用于 AIHR 招聘 MVP 联调。"
    doc.aihr_priority = "High"
    doc.aihr_work_mode = "Hybrid"
    doc.aihr_work_city = "上海"
    doc.aihr_work_schedule = "周一至周五 10:00-19:00"
    doc.aihr_salary_currency = "CNY"
    doc.aihr_salary_min = 25000
    doc.aihr_salary_max = 35000
    doc.aihr_must_have_skills = "recruiting, onboarding, payroll, excel"
    doc.aihr_nice_to_have_skills = "employee relations, communication"
    doc.aihr_agency_brief = build_agency_brief(
        {
            "designation": designation,
            "department": department,
            "work_city": "上海",
            "work_mode": "Hybrid",
            "work_schedule": "周一至周五 10:00-19:00",
            "salary_currency": "CNY",
            "salary_min": "25000",
            "salary_max": "35000",
            "must_have_skills": "recruiting, onboarding, payroll, excel",
            "nice_to_have_skills": "employee relations, communication",
            "reason_for_requesting": "用于 AIHR 招聘 MVP 联调。",
        }
    )
    doc.save(ignore_permissions=True)
    return doc


def _get_or_create_job_opening(company: str, department: str, designation: str, requisition: str):
    existing = frappe.db.exists("Job Opening", {"job_requisition": requisition})
    if existing:
        return frappe.get_doc("Job Opening", existing)

    doc = frappe.new_doc("Job Opening")
    doc.job_title = "HRBP - AIHR MVP Demo"
    doc.company = company
    doc.status = "Open"
    doc.designation = designation
    doc.department = department
    doc.job_requisition = requisition
    doc.vacancies = 1
    doc.description = "负责招聘流程协同、候选人推进、Offer 跟进、入职准备。"
    doc.currency = "CNY"
    doc.lower_range = 25000
    doc.upper_range = 35000
    doc.aihr_channel_mix = "代理公司, 内推, 招聘网站"
    doc.aihr_next_action = "收集第一批候选人简历"
    doc.aihr_agency_pack = frappe.db.get_value("Job Requisition", requisition, "aihr_agency_brief")
    doc.save(ignore_permissions=True)
    return doc


def _get_or_create_job_applicant(job_opening: str, sample: dict[str, Any]):
    existing = frappe.db.exists("Job Applicant", {"email_id": sample["email_id"]})
    if existing:
        return frappe.get_doc("Job Applicant", existing)

    doc = frappe.new_doc("Job Applicant")
    doc.applicant_name = sample["applicant_name"]
    doc.email_id = sample["email_id"]
    doc.status = "Open"
    doc.job_title = job_opening
    doc.phone_number = sample["phone_number"]
    doc.country = "China"
    doc.aihr_resume_text = sample["resume_text"]
    doc.aihr_ai_status = "Not Screened"
    doc.save(ignore_permissions=True)
    return doc


def _screen_applicant(applicant, requisition, job_opening) -> None:
    parsed_resume = parse_resume_text(applicant.aihr_resume_text or "")
    screening = screen_candidate(
        parsed_resume=parsed_resume,
        job_requirements="\n".join(
            filter(
                None,
                [
                    requisition.description,
                    requisition.aihr_must_have_skills,
                    requisition.aihr_nice_to_have_skills,
                ],
            )
        ),
        preferred_skills=requisition.aihr_nice_to_have_skills or "",
        preferred_city=requisition.aihr_work_city or "",
    )

    applicant.aihr_ai_status = "Screened"
    applicant.aihr_match_score = screening["overall_score"]
    applicant.aihr_candidate_city = parsed_resume.get("city", "")
    applicant.aihr_years_experience = parsed_resume.get("years_of_experience", 0)
    applicant.aihr_next_action = "经理初筛"
    applicant.save(ignore_permissions=True)

    existing = frappe.db.exists("AI Screening", {"job_applicant": applicant.name})
    doc = frappe.get_doc("AI Screening", existing) if existing else frappe.new_doc("AI Screening")
    doc.job_applicant = applicant.name
    doc.job_opening = job_opening.name
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


def _ensure_interview_round(designation: str):
    round_name = "AIHR 首轮面试"
    existing = frappe.db.exists("Interview Round", round_name)
    if existing:
        return frappe.get_doc("Interview Round", existing)

    for skill_name, description in (
        ("招聘协同", "能够独立推进招聘全链路协同"),
        ("入职推进", "能承接 Offer 到入职交接的动作"),
        ("业务沟通", "能与部门经理和候选人高效协作"),
    ):
        _ensure_skill(skill_name, description)

    doc = frappe.new_doc("Interview Round")
    doc.round_name = round_name
    doc.designation = designation
    doc.expected_average_rating = 4
    for skill_name in ("招聘协同", "入职推进", "业务沟通"):
        doc.append("expected_skill_set", {"skill": skill_name})
    doc.save(ignore_permissions=True)
    return doc


def _ensure_skill(skill_name: str, description: str):
    existing = frappe.db.exists("Skill", skill_name)
    if existing:
        return frappe.get_doc("Skill", existing)

    doc = frappe.new_doc("Skill")
    doc.skill_name = skill_name
    doc.description = description
    doc.save(ignore_permissions=True)
    return doc


def _get_or_create_interview(job_opening, applicant, interview_round, follow_up_owner: str):
    existing = frappe.db.exists("Interview", {"job_applicant": applicant.name, "interview_round": interview_round.name})
    if existing:
        doc = frappe.get_doc("Interview", existing)
        today = now_datetime().date()
        if str(getattr(doc, "scheduled_on", "")) != str(today):
            doc.db_set("scheduled_on", today, update_modified=False)
        if str(getattr(doc, "from_time", "")) != "14:00:00":
            doc.db_set("from_time", "14:00:00", update_modified=False)
        if str(getattr(doc, "to_time", "")) != "15:00:00":
            doc.db_set("to_time", "15:00:00", update_modified=False)
        updates_needed = False
        if not getattr(doc, "aihr_interview_mode", None):
            doc.aihr_interview_mode = "Video"
            updates_needed = True
        if not getattr(doc, "aihr_follow_up_owner", None):
            doc.aihr_follow_up_owner = follow_up_owner
            updates_needed = True
        feedback_due_at = get_datetime(f"{add_to_date(today, days=1)} 12:00:00")
        if not getattr(doc, "aihr_feedback_due_at", None) or str(doc.aihr_feedback_due_at) != str(feedback_due_at):
            doc.aihr_feedback_due_at = feedback_due_at
            updates_needed = True
        if not getattr(doc, "interview_details", None):
            doc.append("interview_details", {"interviewer": follow_up_owner})
            updates_needed = True
        if updates_needed:
            doc.save(ignore_permissions=True)
        else:
            doc.reload()
        return doc

    screening_name = frappe.db.get_value("AI Screening", {"job_applicant": applicant.name}, "name")
    screening = frappe.get_doc("AI Screening", screening_name) if screening_name else None

    doc = frappe.new_doc("Interview")
    doc.job_applicant = applicant.name
    doc.interview_round = interview_round.name
    doc.scheduled_on = now_datetime().date()
    doc.from_time = "14:00:00"
    doc.to_time = "15:00:00"
    doc.status = "Under Review"
    doc.aihr_interview_mode = "Video"
    doc.aihr_follow_up_owner = follow_up_owner
    doc.aihr_feedback_due_at = get_datetime(f"{add_to_date(doc.scheduled_on, days=1)} 12:00:00")
    doc.append("interview_details", {"interviewer": follow_up_owner})
    doc.aihr_interviewer_pack = build_interviewer_pack(
        candidate_name=applicant.applicant_name,
        opening_title=job_opening.job_title,
        interview_round=interview_round.name,
        interview_mode="视频",
        schedule_label=f"{doc.scheduled_on} 14:00 - 15:00",
        ai_summary=screening.ai_summary if screening else "",
        strengths=(screening.strengths or "").splitlines() if screening else [],
        risks=(screening.risks or "").splitlines() if screening else [],
        suggested_questions=(screening.suggested_questions or "").splitlines() if screening else [],
    )
    doc.save(ignore_permissions=True)
    return doc


def _get_or_create_interview_feedback(interview, interviewer: str):
    existing = frappe.db.exists("Interview Feedback", {"interview": interview.name, "interviewer": interviewer})
    if existing:
        doc = frappe.get_doc("Interview Feedback", existing)
        if doc.docstatus == 0:
            try:
                doc.submit()
                doc.reload()
            except Exception:
                pass
        return doc

    doc = frappe.new_doc("Interview Feedback")
    doc.interview = interview.name
    doc.interviewer = interviewer
    doc.result = "Cleared"
    doc.feedback = "候选人在招聘协同、入职推进和业务沟通上表现稳定，建议进入 Offer 评估。"
    for skill_name, rating in (
        ("招聘协同", 4),
        ("入职推进", 4),
        ("业务沟通", 5),
    ):
        doc.append("skill_assessment", {"skill": skill_name, "rating": rating})
    doc.aihr_hiring_recommendation = "Yes"
    doc.aihr_next_step_suggestion = "同步面试结论并推进 Offer 评估"
    doc.insert(ignore_permissions=True)
    try:
        doc.submit()
    except Exception:
        pass
    return doc


def _get_or_create_job_offer(company: str, designation: str, applicant, job_opening, onboarding_owner: str):
    existing = frappe.db.exists("Job Offer", {"job_applicant": applicant.name})
    if existing:
        doc = frappe.get_doc("Job Offer", existing)
        doc.status = "Accepted"
        doc.aihr_onboarding_owner = onboarding_owner
        doc.aihr_payroll_handoff_status = "Ready"
        doc.aihr_compensation_notes = (
            f"{applicant.applicant_name} 当前岗位匹配度较高，建议按 {job_opening.currency} "
            f"{int(job_opening.lower_range)} - {int(job_opening.upper_range)} 范围沟通最终薪酬。"
        )
        doc.save(ignore_permissions=True)
        return doc

    doc = frappe.new_doc("Job Offer")
    doc.job_applicant = applicant.name
    doc.offer_date = now_datetime().date()
    doc.designation = designation
    doc.company = company
    doc.status = "Accepted"
    doc.terms = (
        "<p>预计到岗时间 2 周内，试用期 3 个月，薪资结构以正式 Offer 为准。</p>"
        "<p>请同步确认身份证明、学历材料、入职日期和薪酬建档负责人。</p>"
    )
    doc.aihr_onboarding_owner = onboarding_owner
    doc.aihr_payroll_handoff_status = "Ready"
    doc.aihr_compensation_notes = (
        f"{applicant.applicant_name} 当前岗位匹配度较高，建议按 {job_opening.currency} "
        f"{int(job_opening.lower_range)} - {int(job_opening.upper_range)} 范围沟通最终薪酬。"
    )
    doc.save(ignore_permissions=True)
    return doc


def _get_or_create_employee_onboarding(job_offer, applicant, job_opening, handoff_owner: str):
    existing = frappe.db.exists("Employee Onboarding", {"job_offer": job_offer.name})
    if existing:
        doc = frappe.get_doc("Employee Onboarding", existing)
        if not getattr(doc, "activities", None):
            for activity in default_onboarding_activities(handoff_owner):
                doc.append("activities", activity)
        doc.aihr_handoff_owner = handoff_owner
        doc.aihr_payroll_ready = 1
        doc.aihr_preboarding_notes = (
            f"{applicant.applicant_name} 的 Offer 已接受，已进入入职交接阶段。"
            " 请核对资料、设备和首月薪酬建档信息。"
        )
        doc.boarding_status = "In Process"
        doc.save(ignore_permissions=True)
        return doc

    doc = frappe.new_doc("Employee Onboarding")
    doc.job_applicant = applicant.name
    doc.job_offer = job_offer.name
    doc.company = job_offer.company
    doc.employee_name = applicant.applicant_name
    doc.department = job_opening.department
    doc.designation = job_offer.designation
    doc.date_of_joining = add_to_date(now_datetime().date(), days=14)
    doc.boarding_begins_on = add_to_date(doc.date_of_joining, days=-7)
    doc.boarding_status = "In Process"
    doc.notify_users_by_email = 0
    doc.aihr_handoff_owner = handoff_owner
    doc.aihr_payroll_ready = 1
    doc.aihr_preboarding_notes = (
        f"{applicant.applicant_name} 的 Offer 已接受，已进入入职交接阶段。"
        " 请核对资料、设备和首月薪酬建档信息。"
    )
    for activity in default_onboarding_activities(handoff_owner):
        doc.append("activities", activity)
    doc.save(ignore_permissions=True)
    return doc


def _candidate_samples() -> list[dict[str, str]]:
    return [
        {
            "applicant_name": "Jane Smith",
            "email_id": "jane.demo@aihr.local",
            "phone_number": "+86 13800138000",
            "resume_text": (
                "Jane Smith\n"
                "jane.demo@aihr.local\n"
                "+86 13800138000\n"
                "Location: Shanghai\n"
                "6 years of experience in recruiting, onboarding, payroll, excel, and employee relations."
            ),
        },
        {
            "applicant_name": "Leo Chen",
            "email_id": "leo.demo@aihr.local",
            "phone_number": "+86 13900139000",
            "resume_text": (
                "Leo Chen\n"
                "leo.demo@aihr.local\n"
                "+86 13900139000\n"
                "Location: Suzhou\n"
                "4 years of experience in recruiting, sourcing, interviewing, excel, and operations."
            ),
        },
        {
            "applicant_name": "Mia Zhang",
            "email_id": "mia.demo@aihr.local",
            "phone_number": "+86 13700137000",
            "resume_text": (
                "Mia Zhang\n"
                "mia.demo@aihr.local\n"
                "+86 13700137000\n"
                "Location: Shanghai\n"
                "7 years of experience in talent acquisition, onboarding, payroll, communication, and project management."
            ),
        },
    ]
