from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import date, datetime
from typing import Any

from aihr.services.screening import build_agency_brief


def generate_requisition_agency_brief(source: Mapping[str, Any] | Any) -> str:
    return build_agency_brief(build_requisition_payload(source))


def build_requisition_payload(source: Mapping[str, Any] | Any) -> dict[str, Any]:
    return {
        "job_title": build_opening_display_title(source),
        "designation": _read(source, "designation"),
        "department": _read(source, "department"),
        "work_city": _read(source, "aihr_work_city") or _read(source, "work_city"),
        "work_mode": _read(source, "aihr_work_mode") or _read(source, "work_mode"),
        "work_schedule": _read(source, "aihr_work_schedule") or _read(source, "work_schedule"),
        "salary_currency": _read(source, "aihr_salary_currency") or _read(source, "salary_currency"),
        "salary_min": _read(source, "aihr_salary_min") or _read(source, "salary_min"),
        "salary_max": _read(source, "aihr_salary_max") or _read(source, "salary_max"),
        "must_have_skills": _read(source, "aihr_must_have_skills") or _read(source, "must_have_skills"),
        "nice_to_have_skills": _read(source, "aihr_nice_to_have_skills") or _read(source, "nice_to_have_skills"),
        "reason_for_requesting": _read(source, "reason_for_requesting") or _read(source, "hiring_goal"),
    }


def build_opening_display_title(source: Mapping[str, Any] | Any) -> str:
    return (
        _read(source, "job_title")
        or _read(source, "designation")
        or _read(source, "designation_name")
        or "未命名岗位"
    )


def evaluate_screening_readiness(source: Mapping[str, Any] | Any) -> dict[str, Any]:
    title = build_opening_display_title(source)
    description = (_read(source, "description") or "").strip()
    must_have = (_read(source, "aihr_must_have_skills") or _read(source, "must_have_skills") or "").strip()
    requisition = (_read(source, "job_requisition") or "").strip()

    missing: list[str] = []
    if not requisition:
        missing.append("岗位需求单")
    if not title or title == "未命名岗位":
        missing.append("岗位名称")
    if not description:
        missing.append("岗位职责说明")
    if not must_have:
        missing.append("必备技能要求")

    return {
        "ready": not missing,
        "opening_title": title,
        "missing_fields": missing,
        "message": (
            "岗位需求已具备 AI 初筛条件。"
            if not missing
            else f"当前还不能进行 AI 初筛，请先补齐：{'、'.join(missing)}。"
        ),
    }


def get_screening_next_action(recommended_status: str) -> str:
    mapping = {
        "Advance": "安排经理初筛",
        "Ready for Review": "经理复核候选人摘要",
        "Hold": "补充信息或暂缓推进",
        "Reject": "确认是否淘汰",
    }
    return mapping.get(recommended_status, "经理初筛")


def build_interviewer_pack(
    *,
    candidate_name: str,
    opening_title: str,
    interview_round: str,
    interview_mode: str,
    schedule_label: str,
    ai_summary: str,
    strengths: Iterable[str] | None = None,
    risks: Iterable[str] | None = None,
    suggested_questions: Iterable[str] | None = None,
) -> str:
    return "\n".join(
        [
            "AIHR 面试官资料包",
            f"候选人：{candidate_name or '待补充'}",
            f"岗位：{opening_title or '待补充'}",
            f"轮次：{interview_round or '待补充'}",
            f"形式：{interview_mode or '待补充'}",
            f"时间：{schedule_label or '待安排'}",
            "",
            "候选人摘要：",
            ai_summary or "暂无 AI 摘要，请先运行候选人 AI 初筛。",
            "",
            "重点优势：",
            *_bullet_lines(strengths, empty_text="待补充"),
            "",
            "潜在风险：",
            *_bullet_lines(risks, empty_text="待补充"),
            "",
            "建议追问：",
            *_bullet_lines(suggested_questions, empty_text="待补充"),
        ]
    ).strip()


def get_interview_follow_up_action(status: str, feedback_due_label: str | None = None) -> str:
    mapping = {
        "Pending": "确认候选人、面试官和会议链接，确保面试如期进行",
        "Under Review": "催收面试反馈并汇总一页结论",
        "Cleared": "推动下一轮或进入 Offer 评估",
        "Rejected": "同步淘汰结论并归档记录",
    }
    action = mapping.get(status, "确认面试安排与后续动作")
    if status == "Under Review" and feedback_due_label:
        return f"{action}，反馈截止 {feedback_due_label}"
    return action


def build_offer_handoff_notes(
    *,
    candidate_name: str,
    opening_title: str,
    offer_status: str,
    onboarding_owner: str,
    payroll_handoff_status: str,
    salary_expectation: str,
    compensation_notes: str,
) -> str:
    manual_notes = compensation_notes or "待确认薪资构成、试用期和补贴项。"
    return "\n".join(
        [
            "AIHR Offer 交接摘要",
            f"候选人：{candidate_name or '待补充'}",
            f"岗位：{opening_title or '待补充'}",
            f"Offer 状态：{offer_status or '待确认'}",
            f"入职交接负责人：{onboarding_owner or '待分配'}",
            f"薪酬交接状态：{payroll_handoff_status or 'Not Started'}",
            f"候选人薪资期望：{salary_expectation or '待补充'}",
            "",
            "当前说明：",
            manual_notes,
            "",
            "建议动作：",
            f"- {get_offer_next_action(offer_status, payroll_handoff_status)}",
            "- 核对 Offer 条款、到岗时间与入职资料清单。",
            "- 将最终薪酬信息同步给入职与薪资建档负责人。",
        ]
    ).strip()


def build_payroll_handoff_summary(
    *,
    candidate_name: str,
    opening_title: str,
    payroll_owner: str,
    payroll_handoff_status: str,
    salary_expectation: str,
    opening_salary_range: str,
    compensation_notes: str,
) -> str:
    return "\n".join(
        [
            "AIHR 薪酬交接摘要",
            f"候选人：{candidate_name or '待补充'}",
            f"岗位：{opening_title or '待补充'}",
            f"薪酬负责人：{payroll_owner or '待分配'}",
            f"当前状态：{payroll_handoff_status or 'Not Started'}",
            f"候选人期望：{salary_expectation or '待补充'}",
            f"岗位预算：{opening_salary_range or '待补充'}",
            "",
            "薪酬备注：",
            compensation_notes or "待确认 base、试用期薪资、补贴项和发薪口径。",
            "",
            "建议动作：",
            f"- {get_payroll_handoff_next_action(payroll_handoff_status)}",
            "- 核对最终薪资、试用期规则、补贴项和到岗日期。",
            "- 确认数据已经同步到入职交接和员工主档。",
        ]
    ).strip()


def get_offer_next_action(status: str, payroll_handoff_status: str) -> str:
    if status == "Accepted":
        if payroll_handoff_status == "Completed":
            return "确认入职清单、工号与首月薪资信息"
        if payroll_handoff_status == "Ready":
            return "发起入职任务并通知薪资建档负责人"
        return "补齐入职资料并准备薪酬交接"
    if status == "Rejected":
        return "归档 Offer 结果并回流岗位策略"
    return "跟进候选人反馈并确认到岗时间"


def get_payroll_handoff_next_action(status: str) -> str:
    mapping = {
        "Not Started": "先确认薪资结构、试用期和发薪口径",
        "Ready": "通知薪酬负责人完成建档并回写结果",
        "Completed": "核对首月薪资信息并确认员工档案",
    }
    return mapping.get(status or "Not Started", "先确认薪资结构、试用期和发薪口径")


def get_feedback_next_action(result: str) -> str:
    mapping = {
        "Cleared": "同步面试结论并推进 Offer 评估",
        "Rejected": "同步淘汰结论并归档面试反馈",
    }
    return mapping.get(result, "补充面试反馈后确认下一步")


def build_feedback_summary(
    *,
    interviewer: str,
    result: str,
    average_rating: str,
    feedback: str,
    ratings: Iterable[str] | None = None,
) -> str:
    return "\n".join(
        [
            "AIHR 面试反馈摘要",
            f"面试官：{interviewer or '待补充'}",
            f"面试结论：{result or '待确认'}",
            f"平均评分：{average_rating or '待补充'}",
            "",
            "技能评分：",
            *_bullet_lines(ratings, empty_text="待补充"),
            "",
            "反馈结论：",
            feedback or "待补充面试官反馈。",
        ]
    ).strip()


def default_onboarding_activities(owner: str) -> list[dict[str, Any]]:
    return [
        {
            "activity_name": "确认 Offer 与入职日期",
            "user": owner,
            "begin_on": 0,
            "duration": 1,
            "required_for_employee_creation": 1,
            "description": "确认候选人接受 Offer、到岗日期与联系方式。",
        },
        {
            "activity_name": "准备入职资料清单",
            "user": owner,
            "begin_on": 0,
            "duration": 2,
            "required_for_employee_creation": 1,
            "description": "核对身份证明、学历材料、银行卡与紧急联系人信息。",
        },
        {
            "activity_name": "同步薪酬建档信息",
            "user": owner,
            "begin_on": 1,
            "duration": 1,
            "required_for_employee_creation": 1,
            "description": "确认薪资结构、试用期、补贴项并同步给薪酬负责人。",
        },
        {
            "activity_name": "准备入职首日安排",
            "user": owner,
            "begin_on": 2,
            "duration": 1,
            "required_for_employee_creation": 0,
            "description": "确认座位、设备、邮箱账号和直属经理对接安排。",
        },
    ]


def build_onboarding_summary(
    *,
    candidate_name: str,
    opening_title: str,
    handoff_owner: str,
    boarding_status: str,
    payroll_ready: bool,
    date_of_joining: str,
    activities: Iterable[str] | None = None,
    preboarding_notes: str = "",
) -> str:
    return "\n".join(
        [
            "AIHR 入职交接摘要",
            f"候选人：{candidate_name or '待补充'}",
            f"岗位：{opening_title or '待补充'}",
            f"交接负责人：{handoff_owner or '待分配'}",
            f"当前状态：{boarding_status or 'Pending'}",
            f"预计入职日期：{date_of_joining or '待确认'}",
            f"薪酬建档是否就绪：{'是' if payroll_ready else '否'}",
            "",
            "关键活动：",
            *_bullet_lines(activities, empty_text="待生成"),
            "",
            "预入职说明：",
            preboarding_notes or "待补充入职资料、设备和薪酬交接说明。",
        ]
    ).strip()


def get_onboarding_next_action(boarding_status: str, payroll_ready: bool) -> str:
    if boarding_status == "Completed":
        return "确认员工档案与首月薪资信息"
    if payroll_ready:
        return "推进入职活动并创建员工档案"
    return "先补齐预入职资料和薪酬建档信息"


def split_person_name(full_name: str) -> tuple[str, str, str]:
    normalized = " ".join(str(full_name or "").strip().split())
    if not normalized:
        return ("AIHR", "", "Employee")
    if " " not in normalized:
        return (normalized, "", "")

    parts = normalized.split(" ")
    if len(parts) == 2:
        return (parts[0], "", parts[1])
    return (parts[0], " ".join(parts[1:-1]), parts[-1])


def resolve_employee_status(date_of_joining: Any, *, today_value: Any = None) -> str:
    joining_date = _normalize_date(date_of_joining)
    anchor = _normalize_date(today_value) or date.today()
    if joining_date and joining_date > anchor:
        return "Inactive"
    return "Active"


def _bullet_lines(items: Iterable[str] | None, *, empty_text: str) -> list[str]:
    normalized = [str(item).strip() for item in (items or []) if str(item).strip()]
    if not normalized:
        return [f"- {empty_text}"]
    return [f"- {item}" for item in normalized]


def _read(source: Mapping[str, Any] | Any, fieldname: str) -> Any:
    if isinstance(source, Mapping):
        return source.get(fieldname)
    return getattr(source, fieldname, None)


def _normalize_date(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = str(value).strip()
    if not text:
        return None
    return date.fromisoformat(text[:10])
