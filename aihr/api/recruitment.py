from __future__ import annotations

from collections import defaultdict
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


if frappe:
    whitelist = frappe.whitelist
else:  # pragma: no cover - local tests do not load Frappe
    def whitelist(*args, **kwargs):
        def decorator(fn):
            return fn

        return decorator


@whitelist()
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


@whitelist()
def build_requisition_agency_brief(payload: dict[str, Any]) -> str:
    return build_agency_brief(payload)


@whitelist()
def get_hiring_hq_snapshot() -> dict[str, Any]:
    if not frappe:
        raise RuntimeError("Frappe is required for fetching AIHR workspace snapshots.")

    from frappe.utils import add_to_date, get_url_to_form, now_datetime, today

    openings = frappe.get_all(
        "Job Opening",
        fields=[
            "name",
            "job_title",
            "status",
            "job_requisition",
            "department",
            "aihr_next_action",
            "aihr_posting_owner",
            "modified",
        ],
        filters={"status": "Open"},
        order_by="modified desc",
        limit_page_length=20,
    )
    requisitions = frappe.get_all(
        "Job Requisition",
        fields=[
            "name",
            "designation",
            "department",
            "status",
            "aihr_priority",
            "aihr_work_city",
            "aihr_work_mode",
            "aihr_agency_brief",
            "modified",
        ],
        order_by="modified desc",
        limit_page_length=20,
    )
    requisition_by_name = {item["name"]: item for item in requisitions}

    applicants = frappe.get_all(
        "Job Applicant",
        fields=[
            "name",
            "applicant_name",
            "job_title",
            "status",
            "aihr_ai_status",
            "aihr_match_score",
            "aihr_candidate_city",
            "aihr_next_action",
            "modified",
        ],
        order_by="aihr_match_score desc, modified desc",
        limit_page_length=200,
    )
    screenings = frappe.get_all(
        "AI Screening",
        fields=[
            "name",
            "job_applicant",
            "job_opening",
            "status",
            "overall_score",
            "modified",
        ],
        order_by="modified desc",
        limit_page_length=200,
    )

    applicants_by_opening: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for applicant in applicants:
        if applicant.get("job_title"):
            applicants_by_opening[applicant["job_title"]].append(applicant)

    screening_by_applicant: dict[str, dict[str, Any]] = {}
    screenings_by_opening: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for screening in screenings:
        if screening.get("job_applicant") and screening["job_applicant"] not in screening_by_applicant:
            screening_by_applicant[screening["job_applicant"]] = screening
        if screening.get("job_opening"):
            screenings_by_opening[screening["job_opening"]].append(screening)

    screened_count = len(screening_by_applicant)
    total_applicants = len(applicants)
    coverage = round((screened_count / total_applicants) * 100) if total_applicants else 0
    ready_count = sum(1 for screening in screenings if screening.get("status") == "Ready for Review")
    advance_count = sum(1 for screening in screenings if screening.get("status") == "Advance")
    hold_count = sum(1 for screening in screenings if screening.get("status") == "Hold")
    unscreened_count = max(total_applicants - screened_count, 0)

    week_start = today()
    week_end = add_to_date(week_start, days=6)
    interviews_this_week = frappe.db.count(
        "Interview",
        {"scheduled_on": ["between", [week_start, week_end]]},
    )

    active_requisitions = [item for item in requisitions if _is_active_requisition(item.get("status"))]
    hot_openings = []
    for opening in openings[:6]:
        linked_applicants = applicants_by_opening.get(opening["name"], [])
        linked_screenings = screenings_by_opening.get(opening["name"], [])
        requisition = requisition_by_name.get(opening.get("job_requisition"))
        scores = [float(screening.get("overall_score") or 0) for screening in linked_screenings if screening.get("overall_score") is not None]
        review_queue = sum(1 for screening in linked_screenings if screening.get("status") == "Ready for Review")
        hot_openings.append(
            {
                "title": opening.get("job_title") or opening["name"],
                "meta": " / ".join(
                    part
                    for part in [
                        requisition.get("department") if requisition else opening.get("department"),
                        requisition.get("aihr_work_city") if requisition else "",
                        requisition.get("aihr_work_mode") if requisition else "",
                    ]
                    if part
                )
                or "招聘中岗位",
                "priority": _priority_label(requisition.get("aihr_priority") if requisition else ""),
                "total_candidates": len(linked_applicants),
                "top_score": f"{max(scores):.0f}" if scores else "--",
                "review_queue": review_queue,
                "next_action": opening.get("aihr_next_action") or "推进第一批候选人",
                "route": get_url_to_form("Job Opening", opening["name"]),
            }
        )

    focus_queue: list[dict[str, Any]] = []
    for requisition in sorted(active_requisitions, key=_requisition_priority_rank)[:2]:
        if not (requisition.get("aihr_agency_brief") or "").strip():
            focus_queue.append(
                {
                    "title": requisition.get("designation") or requisition["name"],
                    "meta": "岗位需求单尚未形成可投递的代理发布包",
                    "kind": "需求单",
                    "action": "补齐 JD、薪资和工作信息后刷新代理发布包",
                    "route": get_url_to_form("Job Requisition", requisition["name"]),
                }
            )

    for opening in hot_openings:
        if opening["total_candidates"] == 0:
            focus_queue.append(
                {
                    "title": opening["title"],
                    "meta": opening["meta"],
                    "kind": "岗位",
                    "action": "尽快收集第一批简历，避免岗位空转",
                    "route": opening["route"],
                }
            )

    for applicant in applicants[:12]:
        screening = screening_by_applicant.get(applicant["name"])
        if not applicant.get("aihr_next_action"):
            continue
        focus_queue.append(
            {
                "title": applicant.get("applicant_name") or applicant["name"],
                "meta": " / ".join(
                    part
                    for part in [
                        applicant.get("job_title"),
                        _candidate_status_label(screening.get("status") if screening else applicant.get("aihr_ai_status") or applicant.get("status")),
                    ]
                    if part
                ),
                "kind": "候选人",
                "action": applicant.get("aihr_next_action") or "确认下一步",
                "route": get_url_to_form("Job Applicant", applicant["name"]),
            }
        )
        if len(focus_queue) >= 6:
            break

    top_candidates = []
    candidates_sorted = sorted(
        applicants,
        key=lambda item: (
            float(item.get("aihr_match_score") or 0),
            str(item.get("modified") or ""),
        ),
        reverse=True,
    )
    for applicant in candidates_sorted[:6]:
        screening = screening_by_applicant.get(applicant["name"])
        top_candidates.append(
            {
                "name": applicant.get("applicant_name") or applicant["name"],
                "job_title": applicant.get("job_title") or "未关联岗位",
                "city": applicant.get("aihr_candidate_city") or "城市待补充",
                "status_label": _candidate_status_label(
                    screening.get("status") if screening else applicant.get("aihr_ai_status") or applicant.get("status")
                ),
                "score": f"{float(applicant.get('aihr_match_score') or 0):.0f}",
                "next_action_short": _truncate_text(applicant.get("aihr_next_action") or "待确认", 10),
                "opening_short": _truncate_text(applicant.get("job_title") or "未关联岗位", 12),
                "next_action": applicant.get("aihr_next_action") or "待确认下一步",
                "route": get_url_to_form("Job Applicant", applicant["name"]),
            }
        )

    return {
        "hero": {
            "title": "AIHR 招聘主链路已接管",
            "subtitle": (
                f"当前共有 {len(active_requisitions)} 条有效岗位需求、{len(openings)} 个招聘中岗位、"
                f"{ready_count + advance_count} 位值得优先推进的候选人。"
            ),
        },
        "metrics": [
            _build_metric("开放岗位需求", len(active_requisitions), "需求单已结构化，可继续补齐岗位信息", "#0f766e"),
            _build_metric("招聘中岗位", len(openings), "当前在跑招聘漏斗的岗位数量", "#ea580c"),
            _build_metric("候选人池", total_applicants, "已进入系统并可追踪状态的候选人", "#2563eb"),
            _build_metric("待经理复核", ready_count, "AI 已完成摘要，等待经理判断", "#d97706"),
            _build_metric("AI 覆盖率", f"{coverage}%", "候选人中已生成摘要卡的比例", "#7c3aed"),
            _build_metric("本周面试", interviews_this_week, "计划在本周完成的面试安排", "#be123c"),
        ],
        "stage_counts": [
            {
                "label": "待 AI 初筛",
                "count": unscreened_count,
                "hint": "先把 PDF 简历转成结构化摘要卡",
                "color": "#475569",
            },
            {
                "label": "待经理复核",
                "count": ready_count,
                "hint": "经理优先看摘要卡，而不是直接翻简历",
                "color": "#f59e0b",
            },
            {
                "label": "建议推进",
                "count": advance_count,
                "hint": "优先安排经理面试或进入下一轮",
                "color": "#0f766e",
            },
            {
                "label": "建议暂缓",
                "count": hold_count,
                "hint": "信息不足或匹配偏弱，需补充判断",
                "color": "#dc2626",
            },
        ],
        "hot_openings": hot_openings,
        "focus_queue": focus_queue[:6],
        "top_candidates": top_candidates,
        "refreshed_at": now_datetime().isoformat(),
    }


@whitelist()
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


@whitelist()
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
            "aihr_candidate_city",
        ],
        order_by="aihr_match_score desc, modified desc",
    )

    screenings = frappe.get_all(
        "AI Screening",
        filters={"job_opening": job_opening},
        fields=["job_applicant", "status", "overall_score"],
        order_by="overall_score desc, modified desc",
    )
    screening_by_applicant = {}
    for item in screenings:
        if item["job_applicant"] not in screening_by_applicant:
            screening_by_applicant[item["job_applicant"]] = item

    status_counts: dict[str, int] = {}
    for applicant in applicants:
        screening = screening_by_applicant.get(applicant["name"])
        status = screening.get("status") if screening else applicant.get("aihr_ai_status") or applicant.get("status") or "Unknown"
        status_counts[status] = status_counts.get(status, 0) + 1

    scores = [float(item.get("overall_score") or 0) for item in screenings if item.get("overall_score") is not None]
    top_candidates = []
    for applicant in applicants[:5]:
        screening = screening_by_applicant.get(applicant["name"])
        top_candidates.append(
            {
                **applicant,
                "pipeline_status": screening.get("status") if screening else applicant.get("aihr_ai_status") or applicant.get("status"),
                "status_label": _candidate_status_label(
                    screening.get("status") if screening else applicant.get("aihr_ai_status") or applicant.get("status")
                ),
                "route": frappe.utils.get_url_to_form("Job Applicant", applicant["name"]),
            }
        )

    return {
        "job_opening": job_opening,
        "total_applicants": len(applicants),
        "status_counts": status_counts,
        "review_queue": status_counts.get("Ready for Review", 0),
        "advance_count": status_counts.get("Advance", 0),
        "hold_count": status_counts.get("Hold", 0),
        "screened_count": len(screenings),
        "unscreened_count": max(len(applicants) - len(screenings), 0),
        "top_score": max(scores) if scores else 0,
        "average_score": round(sum(scores) / len(scores), 1) if scores else 0,
        "top_candidates": top_candidates,
    }


@whitelist()
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


@whitelist()
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


@whitelist()
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


@whitelist()
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


def _build_metric(label: str, value: Any, hint: str, tone: str) -> dict[str, Any]:
    return {
        "label": label,
        "value": value,
        "hint": hint,
        "tone": tone,
    }


def _is_active_requisition(status: str | None) -> bool:
    lowered = (status or "").strip().lower()
    if not lowered:
        return True
    return lowered not in {"cancelled", "closed", "filled", "rejected"}


def _requisition_priority_rank(item: dict[str, Any]) -> tuple[int, str]:
    priority = (item.get("aihr_priority") or "").strip()
    rank_map = {"Critical": 0, "High": 1, "Normal": 2}
    return (rank_map.get(priority, 9), str(item.get("modified") or ""))


def _priority_label(value: str | None) -> str:
    labels = {
        "Critical": "关键补位",
        "High": "优先推进",
        "Normal": "常规推进",
    }
    return labels.get(value or "", "标准岗位")


def _candidate_status_label(value: str | None) -> str:
    labels = {
        "Advance": "建议推进",
        "Ready for Review": "待经理复核",
        "Hold": "建议暂缓",
        "Reject": "建议淘汰",
        "Screened": "已初筛",
        "Not Screened": "未初筛",
        "Manager Review": "经理评估中",
        "Interview": "面试中",
        "Rejected": "已淘汰",
        "Offer": "待发 Offer",
        "Hired": "已录用",
        "Open": "新进入池",
    }
    return labels.get(value or "", value or "待确认")


def _truncate_text(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return f"{value[:limit]}..."
