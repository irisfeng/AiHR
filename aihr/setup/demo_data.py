from __future__ import annotations

from typing import Any

import frappe
from frappe.utils import add_to_date, get_datetime, now_datetime

from aihr.setup.departments import DEMO_MANAGER_ACCOUNTS
from aihr.services.recruitment_ops import (
    build_interviewer_pack,
    build_opening_display_title,
    default_onboarding_activities,
)
from aihr.services.resume_parser import parse_resume_text
from aihr.services.screening import build_agency_brief, screen_candidate


def seed_demo_recruitment_data(company: str) -> dict[str, str]:
    company_doc = _ensure_company(company)
    scenarios = [
        {
            "summary_prefix": "",
            "department_name": "人事部",
            "designation_name": "HRBP",
            "manager_user_id": "manager.demo@aihr.local",
            "job_title": "HRBP - AIHR MVP Demo",
            "requisition_description": "负责招聘、入职、组织协同，支持 AIHR 系统试运行。",
            "requisition_reason": "用于 AIHR 招聘 MVP 联调。",
            "work_city": "上海",
            "work_mode": "Hybrid",
            "work_schedule": "周一至周五 10:00-19:00",
            "salary_min": 25000,
            "salary_max": 35000,
            "must_have_skills": "recruiting, onboarding, payroll, excel",
            "nice_to_have_skills": "employee relations, communication",
            "opening_description": "负责招聘流程协同、候选人推进、Offer 跟进、入职准备。",
            "channel_mix": "代理公司, 内推, 招聘网站",
            "next_action": "收集第一批候选人简历",
            "interview_round_name": "AIHR 首轮面试",
            "interview_skill_set": (
                ("招聘协同", "能够独立推进招聘全链路协同"),
                ("入职推进", "能承接 Offer 到入职交接的动作"),
                ("业务沟通", "能与部门经理和候选人高效协作"),
            ),
            "feedback_text": "候选人在招聘协同、入职推进和业务沟通上表现稳定，建议进入 Offer 评估。",
            "feedback_skill_ratings": (("招聘协同", 4), ("入职推进", 4), ("业务沟通", 5)),
            "feedback_next_step": "同步面试结论并推进 Offer 评估",
            "candidate_samples": _candidate_samples(),
        },
        {
            "summary_prefix": "delivery_",
            "department_name": "交付中心",
            "designation_name": "交付工程师",
            "manager_user_id": "delivery.manager@aihr.local",
            "job_title": "交付工程师 - AIHR Demo",
            "requisition_description": "负责客户交付实施、运维排障、部署上线与跨团队交付协同。",
            "requisition_reason": "用于交付中心经理视角联调与权限验证。",
            "work_city": "上海",
            "work_mode": "Onsite",
            "work_schedule": "周一至周五 09:30-18:30，必要时支持项目现场交付",
            "salary_min": 18000,
            "salary_max": 28000,
            "must_have_skills": "交付, 实施, 运维, linux, docker, nginx, mysql, redis, shell",
            "nice_to_have_skills": "kubernetes, ansible, 监控, 技术支持, 客户沟通",
            "opening_description": "负责项目交付上线、客户环境部署、故障排查与日常运维支持。",
            "channel_mix": "供应商, 内推, 老员工推荐",
            "next_action": "导入第一批交付中心候选人并安排经理复核",
            "interview_round_name": "AIHR 交付首轮面试",
            "interview_skill_set": (
                ("交付实施", "能独立承担交付上线与实施部署"),
                ("运维排障", "能快速定位并解决部署与运行问题"),
                ("客户沟通", "能与客户及内部团队稳定协同推进项目"),
            ),
            "feedback_text": "候选人在交付实施与运维排障方面匹配度较高，具备推进客户项目上线的基础能力。",
            "feedback_skill_ratings": (("交付实施", 5), ("运维排障", 4), ("客户沟通", 4)),
            "feedback_next_step": "安排交付中心经理二次复核并确认项目经历深度",
            "candidate_samples": _delivery_candidate_samples(),
        },
    ]

    summary: dict[str, str] = {"company": company_doc.name}
    for scenario in scenarios:
        scenario_result = _seed_department_scenario(company_doc.name, scenario)
        summary.update(scenario_result)
    return summary


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


def _ensure_requester(
    company: str,
    department: str,
    designation: str,
    user_id: str = "manager.demo@aihr.local",
    first_name: str = "Hiring",
    last_name: str = "Manager",
    password: str = "AIHRDemo!2026",
):
    employee_name = frappe.db.get_value("Employee", {"user_id": user_id})
    if employee_name:
        return frappe.get_doc("Employee", employee_name)

    if not frappe.db.exists("User", user_id):
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": user_id,
                "first_name": first_name,
                "last_name": last_name,
                "new_password": password,
                "send_welcome_email": 0,
            }
        )
        user.insert(ignore_permissions=True)

    employee = frappe.get_doc(
        {
            "doctype": "Employee",
            "naming_series": "HR-EMP-",
            "first_name": first_name,
            "last_name": last_name,
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


def _get_or_create_requisition(
    company: str,
    department: str,
    designation: str,
    requested_by: str,
    *,
    expected_compensation: int = 30000,
    description: str = "负责招聘、入职、组织协同，支持 AIHR 系统试运行。",
    reason_for_requesting: str = "用于 AIHR 招聘 MVP 联调。",
    priority: str = "High",
    work_mode: str = "Hybrid",
    work_city: str = "上海",
    work_schedule: str = "周一至周五 10:00-19:00",
    salary_currency: str = "CNY",
    salary_min: int = 25000,
    salary_max: int = 35000,
    must_have_skills: str = "recruiting, onboarding, payroll, excel",
    nice_to_have_skills: str = "employee relations, communication",
):
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
    doc.expected_compensation = expected_compensation
    doc.company = company
    doc.status = "Open & Approved"
    doc.description = description
    doc.reason_for_requesting = reason_for_requesting
    doc.aihr_priority = priority
    doc.aihr_work_mode = work_mode
    doc.aihr_work_city = work_city
    doc.aihr_work_schedule = work_schedule
    doc.aihr_salary_currency = salary_currency
    doc.aihr_salary_min = salary_min
    doc.aihr_salary_max = salary_max
    doc.aihr_must_have_skills = must_have_skills
    doc.aihr_nice_to_have_skills = nice_to_have_skills
    doc.aihr_agency_brief = build_agency_brief(
        {
            "designation": designation,
            "department": department,
            "work_city": work_city,
            "work_mode": work_mode,
            "work_schedule": work_schedule,
            "salary_currency": salary_currency,
            "salary_min": str(salary_min),
            "salary_max": str(salary_max),
            "must_have_skills": must_have_skills,
            "nice_to_have_skills": nice_to_have_skills,
            "reason_for_requesting": reason_for_requesting,
        }
    )
    doc.save(ignore_permissions=True)
    return doc


def _get_or_create_job_opening(
    company: str,
    department: str,
    designation: str,
    requisition: str,
    *,
    job_title: str = "HRBP - AIHR MVP Demo",
    description: str = "负责招聘流程协同、候选人推进、Offer 跟进、入职准备。",
    currency: str = "CNY",
    lower_range: int = 25000,
    upper_range: int = 35000,
    channel_mix: str = "代理公司, 内推, 招聘网站",
    next_action: str = "收集第一批候选人简历",
):
    existing = frappe.db.exists("Job Opening", {"job_requisition": requisition})
    if existing:
        return frappe.get_doc("Job Opening", existing)

    doc = frappe.new_doc("Job Opening")
    doc.job_title = job_title
    doc.company = company
    doc.status = "Open"
    doc.designation = designation
    doc.department = department
    doc.job_requisition = requisition
    doc.vacancies = 1
    doc.description = description
    doc.currency = currency
    doc.lower_range = lower_range
    doc.upper_range = upper_range
    doc.aihr_channel_mix = channel_mix
    doc.aihr_next_action = next_action
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


def _screen_applicant(applicant, requisition, job_opening):
    applicant = frappe.get_doc("Job Applicant", applicant.name)
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
    doc.aihr_candidate_name_snapshot = applicant.applicant_name or applicant.name
    doc.aihr_opening_title_snapshot = build_opening_display_title(job_opening)
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
    return frappe.get_doc("Job Applicant", applicant.name)


def _ensure_interview_round(
    designation: str,
    round_name: str = "AIHR 首轮面试",
    skill_set: tuple[tuple[str, str], ...] | None = None,
):
    existing = frappe.db.exists("Interview Round", round_name)
    if existing:
        return frappe.get_doc("Interview Round", existing)

    configured_skill_set = skill_set or (
        ("招聘协同", "能够独立推进招聘全链路协同"),
        ("入职推进", "能承接 Offer 到入职交接的动作"),
        ("业务沟通", "能与部门经理和候选人高效协作"),
    )

    for skill_name, description in configured_skill_set:
        _ensure_skill(skill_name, description)

    doc = frappe.new_doc("Interview Round")
    doc.round_name = round_name
    doc.designation = designation
    doc.expected_average_rating = 4
    for skill_name, _description in configured_skill_set:
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


def _get_or_create_interview_feedback(
    interview,
    interviewer: str,
    *,
    result: str = "Cleared",
    feedback: str = "候选人在招聘协同、入职推进和业务沟通上表现稳定，建议进入 Offer 评估。",
    skill_ratings: tuple[tuple[str, int], ...] = (("招聘协同", 4), ("入职推进", 4), ("业务沟通", 5)),
    hiring_recommendation: str = "Yes",
    next_step_suggestion: str = "同步面试结论并推进 Offer 评估",
):
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
    doc.result = result
    doc.feedback = feedback
    for skill_name, rating in skill_ratings:
        doc.append("skill_assessment", {"skill": skill_name, "rating": rating})
    doc.aihr_hiring_recommendation = hiring_recommendation
    doc.aihr_next_step_suggestion = next_step_suggestion
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


def _delivery_candidate_samples() -> list[dict[str, str]]:
    return [
        {
            "applicant_name": "陈寒",
            "email_id": "delivery.chenhan@aihr.local",
            "phone_number": "+86 13600136001",
            "resume_text": (
                "陈寒\n"
                "delivery.chenhan@aihr.local\n"
                "+86 13600136001\n"
                "现居上海\n"
                "6年交付实施与运维经验，熟悉 Linux、Docker、Nginx、MySQL、Redis、Shell，"
                "负责过客户环境部署、故障排查、上线交付与日常技术支持。"
            ),
        },
        {
            "applicant_name": "李想",
            "email_id": "delivery.lixiang@aihr.local",
            "phone_number": "+86 13600136002",
            "resume_text": (
                "李想\n"
                "delivery.lixiang@aihr.local\n"
                "+86 13600136002\n"
                "现居杭州\n"
                "4年实施交付经验，熟悉 Linux、Docker、Kubernetes、监控、技术支持、客户沟通，"
                "具备项目上线与问题排障经历。"
            ),
        },
        {
            "applicant_name": "周宁",
            "email_id": "delivery.zhouning@aihr.local",
            "phone_number": "+86 13600136003",
            "resume_text": (
                "周宁\n"
                "delivery.zhouning@aihr.local\n"
                "+86 13600136003\n"
                "现居上海\n"
                "7年交付运维经验，熟悉 实施、交付、Linux、Nginx、MySQL、Redis、Ansible、Shell，"
                "支持过客户项目部署、运维巡检、故障处理与跨团队交付协同。"
            ),
        },
    ]


def _get_manager_profile(user_id: str) -> dict[str, str]:
    return next((item for item in DEMO_MANAGER_ACCOUNTS if item["user_id"] == user_id), {})


def _seed_department_scenario(company: str, scenario: dict[str, Any]) -> dict[str, str]:
    department = _ensure_department(scenario["department_name"], company)
    designation = _ensure_designation(scenario["designation_name"])
    manager_profile = _get_manager_profile(scenario["manager_user_id"])
    requester = _ensure_requester(
        company,
        department.name,
        designation.name,
        user_id=scenario["manager_user_id"],
        first_name=manager_profile.get("first_name", scenario["designation_name"]),
        last_name=manager_profile.get("last_name", "经理"),
        password=manager_profile.get("password", "AIHRDemo!2026"),
    )

    requisition = _get_or_create_requisition(
        company=company,
        department=department.name,
        designation=designation.name,
        requested_by=requester.name,
        expected_compensation=scenario["salary_max"],
        description=scenario["requisition_description"],
        reason_for_requesting=scenario["requisition_reason"],
        work_mode=scenario["work_mode"],
        work_city=scenario["work_city"],
        work_schedule=scenario["work_schedule"],
        salary_min=scenario["salary_min"],
        salary_max=scenario["salary_max"],
        must_have_skills=scenario["must_have_skills"],
        nice_to_have_skills=scenario["nice_to_have_skills"],
    )
    job_opening = _get_or_create_job_opening(
        company=company,
        department=department.name,
        designation=designation.name,
        requisition=requisition.name,
        job_title=scenario["job_title"],
        description=scenario["opening_description"],
        lower_range=scenario["salary_min"],
        upper_range=scenario["salary_max"],
        channel_mix=scenario["channel_mix"],
        next_action=scenario["next_action"],
    )

    applicant_docs = []
    for sample in scenario["candidate_samples"]:
        applicant = _get_or_create_job_applicant(job_opening.name, sample)
        applicant = _screen_applicant(applicant, requisition, job_opening)
        applicant_docs.append(applicant)

    interview_round = _ensure_interview_round(
        designation.name,
        round_name=scenario["interview_round_name"],
        skill_set=scenario["interview_skill_set"],
    )
    interview = _get_or_create_interview(job_opening, applicant_docs[0], interview_round, requester.user_id)
    interview_feedback = _get_or_create_interview_feedback(
        interview,
        requester.user_id,
        feedback=scenario["feedback_text"],
        skill_ratings=scenario["feedback_skill_ratings"],
        next_step_suggestion=scenario["feedback_next_step"],
    )
    job_offer = _get_or_create_job_offer(company, designation.name, applicant_docs[-1], job_opening, requester.user_id)
    employee_onboarding = _get_or_create_employee_onboarding(job_offer, applicant_docs[-1], job_opening, requester.user_id)

    prefix = scenario.get("summary_prefix", "")
    return {
        f"{prefix}job_requisition": requisition.name,
        f"{prefix}job_opening": job_opening.name,
        f"{prefix}job_applicants": ", ".join(applicant.name for applicant in applicant_docs),
        f"{prefix}interview": interview.name,
        f"{prefix}interview_feedback": interview_feedback.name,
        f"{prefix}job_offer": job_offer.name,
        f"{prefix}employee_onboarding": employee_onboarding.name,
    }
