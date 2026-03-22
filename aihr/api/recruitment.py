from __future__ import annotations

from collections import defaultdict
from hashlib import sha1
from pathlib import Path
from typing import Any

from aihr.services.ai_assistant import (
    build_interviewer_pack_with_llm,
    enhance_screening_with_llm,
    summarize_interview_feedback_with_llm,
)
from aihr.services.recruitment_ops import (
    build_opening_display_title,
    build_interviewer_pack,
    build_feedback_summary,
    build_offer_handoff_notes,
    build_onboarding_summary,
    build_payroll_handoff_summary,
    default_onboarding_activities,
    generate_requisition_agency_brief,
    evaluate_screening_readiness,
    get_feedback_next_action,
    get_interview_follow_up_action,
    get_onboarding_next_action,
    get_offer_next_action,
    get_payroll_handoff_next_action,
    get_screening_next_action,
    resolve_employee_status,
    split_person_name,
)
from aihr.services.resume_intake import extract_resume_archive, summarize_archive_results
from aihr.services.resume_parser import (
    extract_text_from_file,
    infer_name_from_file_name,
    is_valid_name,
    parse_resume_text,
)
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
    heuristic = screen_candidate(
        parsed_resume=parsed_resume,
        job_requirements=job_requirements,
        preferred_skills=preferred_skills or "",
        preferred_city=preferred_city or "",
    )
    result = enhance_screening_with_llm(
        parsed_resume=parsed_resume,
        resume_text=resume_text,
        opening_title="预览岗位",
        job_requirements=job_requirements,
        preferred_skills=preferred_skills or "",
        preferred_city=preferred_city or "",
        heuristic_screening=heuristic,
    )
    return {
        "parsed_resume": parsed_resume,
        "screening": result,
    }


@whitelist()
def build_requisition_agency_brief(payload: dict[str, Any]) -> str:
    return build_agency_brief(payload)


@whitelist()
def create_resume_intake_batch(
    job_opening: str,
    archive_file: str,
    supplier_name: str | None = None,
    source_channel: str | None = None,
    auto_run_screening: int = 1,
) -> dict[str, Any]:
    if not frappe:
        raise RuntimeError("Frappe is required for importing resume archives.")

    from frappe.utils import now_datetime

    batch_id = f"RIB-{now_datetime().strftime('%Y%m%d%H%M%S')}"
    archive_path = _resolve_file_url_to_path(archive_file)
    opening = frappe.get_doc("Job Opening", job_opening)
    screening_gate = _get_opening_screening_gate(opening)
    archive_items = extract_resume_archive(archive_path)
    archive_summary = summarize_archive_results(archive_items)

    imported_applicants: list[str] = []
    runtime_failed_count = 0
    log_lines = [
        f"批次：{batch_id}",
        f"岗位：{screening_gate['opening_title']}",
        f"来源渠道：{source_channel or '供应商线下包'}",
        f"供应商：{supplier_name or '未填写'}",
    ]
    if not screening_gate["ready"] and int(auto_run_screening or 0):
        log_lines.append(f"AI 初筛待激活：{screening_gate['message']}")

    for item in archive_items:
        if item["status"] != "Parsed":
            log_lines.append(f"{item['file_name']}：{item['status']} - {item.get('reason') or '未处理'}")
            continue

        try:
            applicant, created = _upsert_job_applicant_from_archive_item(
                opening=opening,
                batch_reference=batch_id,
                supplier_name=supplier_name or "",
                source_channel=source_channel or "供应商线下包",
                archive_item=item,
            )
            imported_applicants.append(applicant.name)

            if int(auto_run_screening or 0) and screening_gate["ready"]:
                screen_job_applicant(applicant.name, save=1)
                screening_label = "已生成 AI 摘要"
            elif int(auto_run_screening or 0):
                _mark_applicant_pending_requirements(applicant, screening_gate["message"])
                screening_label = "已入库，待岗位需求完善后生成 AI 摘要"
            elif not screening_gate["ready"]:
                _mark_applicant_pending_requirements(applicant, screening_gate["message"])
                screening_label = "已入库，待岗位需求完善后生成 AI 摘要"
            else:
                screening_label = "已入库，待手动生成 AI 摘要"

            action_label = "新建候选人" if created else "更新候选人"
            log_lines.append(f"{item['file_name']}：{action_label} -> {applicant.name}，{screening_label}")
        except Exception as exc:
            runtime_failed_count += 1
            log_lines.append(f"{item['file_name']}：Failed - {frappe.safe_decode(str(exc))}")

    failed_count = archive_summary["failed_count"] + runtime_failed_count

    if len(imported_applicants) and not failed_count and not archive_summary["unsupported_count"]:
        status = "Completed"
    elif len(imported_applicants):
        status = "Completed With Issues"
    else:
        status = "Failed"

    return {
        "batch": batch_id,
        "status": status,
        "screening_gate": screening_gate,
        "summary": {
            "total_files": archive_summary["total_files"],
            "imported_count": len(imported_applicants),
            "skipped_count": archive_summary["unsupported_count"],
            "failed_count": failed_count,
        },
        "job_applicants": imported_applicants,
        "intake_log": "\n".join(log_lines),
    }


@whitelist()
def process_resume_intake_batch(batch_name: str) -> dict[str, Any]:
    raise NotImplementedError("Persistent batch reprocessing is not enabled in the current MVP.")


@whitelist()
def get_hiring_hq_snapshot() -> dict[str, Any]:
    if not frappe:
        raise RuntimeError("Frappe is required for fetching AIHR workspace snapshots.")

    from frappe.utils import add_to_date, get_url_to_form, now_datetime, today

    openings = frappe.get_list(
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
    requisitions = frappe.get_list(
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
    opening_by_name = {item["name"]: item for item in openings}

    applicants = frappe.get_list(
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
    screenings = frappe.get_list(
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
    interviews_this_week = len(
        frappe.get_list(
            "Interview",
            filters={"scheduled_on": ["between", [week_start, week_end]]},
            fields=["name"],
            limit_page_length=500,
        )
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
                        _opening_title_by_name(opening_by_name, applicant.get("job_title")),
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
                "job_title": _opening_title_by_name(opening_by_name, applicant.get("job_title")),
                "city": applicant.get("aihr_candidate_city") or "城市待补充",
                "status_label": _candidate_status_label(
                    screening.get("status") if screening else applicant.get("aihr_ai_status") or applicant.get("status")
                ),
                "score": f"{float(applicant.get('aihr_match_score') or 0):.0f}",
                "next_action_short": _truncate_text(applicant.get("aihr_next_action") or "待确认", 10),
                "opening_short": _truncate_text(_opening_title_by_name(opening_by_name, applicant.get("job_title")), 12),
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
    _assert_doc_permission(applicant, "read")
    screening_name = frappe.db.get_value("AI Screening", {"job_applicant": applicant.name}, "name")
    screening = frappe.get_doc("AI Screening", screening_name) if screening_name else None
    job_opening = frappe.get_doc("Job Opening", applicant.job_title) if getattr(applicant, "job_title", None) else None
    if job_opening:
        _assert_doc_permission(job_opening, "read")
    screening_gate = _get_opening_screening_gate(job_opening)
    requisition = (
        frappe.get_doc("Job Requisition", job_opening.job_requisition)
        if job_opening and getattr(job_opening, "job_requisition", None)
        else None
    )
    if requisition:
        _assert_doc_permission(requisition, "read")
    if screening:
        _assert_doc_permission(screening, "read")

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
        "screening_gate": screening_gate,
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

    opening = frappe.get_doc("Job Opening", job_opening)
    _assert_doc_permission(opening, "read")
    screening_gate = _get_opening_screening_gate(opening)

    applicants = frappe.get_list(
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

    screenings = frappe.get_list(
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
        "job_opening_title": build_opening_display_title(opening),
        "screening_gate": screening_gate,
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
def get_interview_snapshot(interview: str) -> dict[str, Any]:
    if not frappe:
        raise RuntimeError("Frappe is required for fetching Interview snapshots.")

    interview_doc = frappe.get_doc("Interview", interview)
    _assert_doc_permission(interview_doc, "read")
    applicant = frappe.get_doc("Job Applicant", interview_doc.job_applicant) if getattr(interview_doc, "job_applicant", None) else None
    if applicant:
        _assert_doc_permission(applicant, "read")
    opening = _get_job_opening_doc(getattr(interview_doc, "job_opening", None) or getattr(applicant, "job_title", None))
    if opening:
        _assert_doc_permission(opening, "read")
    screening = _get_latest_screening_doc(applicant.name if applicant else None)
    if screening:
        _assert_doc_permission(screening, "read")

    feedback_due_label = _format_datetime_label(getattr(interview_doc, "aihr_feedback_due_at", None))
    schedule_label = _build_interview_schedule_label(interview_doc)
    next_action = get_interview_follow_up_action(interview_doc.status, feedback_due_label)

    return {
        "interview": {
            "name": interview_doc.name,
            "status": interview_doc.status,
            "interview_round": interview_doc.interview_round,
            "interview_mode": getattr(interview_doc, "aihr_interview_mode", ""),
            "scheduled_on": interview_doc.scheduled_on,
            "from_time": interview_doc.from_time,
            "to_time": interview_doc.to_time,
            "schedule_label": schedule_label,
            "follow_up_owner": getattr(interview_doc, "aihr_follow_up_owner", ""),
            "feedback_due_at": getattr(interview_doc, "aihr_feedback_due_at", ""),
            "feedback_due_label": feedback_due_label,
            "interviewer_pack": getattr(interview_doc, "aihr_interviewer_pack", ""),
            "interview_summary": interview_doc.interview_summary,
            "interviewers": [row.interviewer for row in getattr(interview_doc, "interview_details", []) if getattr(row, "interviewer", None)],
        },
        "job_applicant": {
            "name": applicant.name,
            "applicant_name": applicant.applicant_name,
            "email_id": applicant.email_id,
            "phone_number": applicant.phone_number,
            "aihr_ai_status": getattr(applicant, "aihr_ai_status", ""),
            "aihr_next_action": getattr(applicant, "aihr_next_action", ""),
            "aihr_match_score": getattr(applicant, "aihr_match_score", 0),
        }
        if applicant
        else None,
        "job_opening": {
            "name": opening.name,
            "job_title": opening.job_title,
            "company": opening.company,
        }
        if opening
        else None,
        "screening": {
            "status": screening.status,
            "overall_score": screening.overall_score,
            "ai_summary": screening.ai_summary,
            "strengths": _lines_to_list(screening.strengths),
            "risks": _lines_to_list(screening.risks),
            "suggested_questions": _lines_to_list(screening.suggested_questions),
        }
        if screening
        else None,
        "actions": {
            "next_action": next_action,
            "candidate_route": frappe.utils.get_url_to_form("Job Applicant", applicant.name) if applicant else "",
            "opening_route": frappe.utils.get_url_to_form("Job Opening", opening.name) if opening else "",
        },
    }


@whitelist()
def prepare_interviewer_pack(interview: str, save: int = 1) -> dict[str, Any]:
    if not frappe:
        raise RuntimeError("Frappe is required for preparing Interview records.")

    interview_doc = frappe.get_doc("Interview", interview)
    applicant = frappe.get_doc("Job Applicant", interview_doc.job_applicant) if getattr(interview_doc, "job_applicant", None) else None
    opening = _get_job_opening_doc(getattr(interview_doc, "job_opening", None) or getattr(applicant, "job_title", None))
    screening = _get_latest_screening_doc(applicant.name if applicant else None)

    feedback_due_at = getattr(interview_doc, "aihr_feedback_due_at", None) or _default_feedback_due_at(interview_doc.scheduled_on)
    if not getattr(interview_doc, "aihr_follow_up_owner", None):
        interview_doc.aihr_follow_up_owner = _default_owner()
    interview_doc.aihr_feedback_due_at = feedback_due_at
    pack = _build_interviewer_pack_for_context(interview_doc, applicant, opening, screening)

    if save:
        interview_doc.aihr_interviewer_pack = pack
        interview_doc.save(ignore_permissions=True)

    return {
        "interview": interview_doc.name,
        "interviewer_pack": pack,
        "feedback_due_at": feedback_due_at,
        "follow_up_owner": interview_doc.aihr_follow_up_owner,
    }


@whitelist()
def sync_interview_follow_up(interview: str, save: int = 1) -> dict[str, Any]:
    if not frappe:
        raise RuntimeError("Frappe is required for syncing Interview follow-up.")

    interview_doc = frappe.get_doc("Interview", interview)
    applicant = frappe.get_doc("Job Applicant", interview_doc.job_applicant) if getattr(interview_doc, "job_applicant", None) else None

    if not getattr(interview_doc, "aihr_follow_up_owner", None):
        interview_doc.aihr_follow_up_owner = _default_owner()
    if not getattr(interview_doc, "aihr_feedback_due_at", None):
        interview_doc.aihr_feedback_due_at = _default_feedback_due_at(interview_doc.scheduled_on)

    next_action = get_interview_follow_up_action(
        interview_doc.status,
        _format_datetime_label(getattr(interview_doc, "aihr_feedback_due_at", None)),
    )

    if save:
        if not getattr(interview_doc, "aihr_interviewer_pack", None):
            opening = _get_job_opening_doc(getattr(interview_doc, "job_opening", None) or getattr(applicant, "job_title", None))
            screening = _get_latest_screening_doc(applicant.name if applicant else None)
            interview_doc.aihr_interviewer_pack = _build_interviewer_pack_for_context(interview_doc, applicant, opening, screening)
        interview_doc.save(ignore_permissions=True)

    return {
        "interview": interview_doc.name,
        "next_action": next_action,
        "follow_up_owner": getattr(interview_doc, "aihr_follow_up_owner", ""),
        "feedback_due_at": getattr(interview_doc, "aihr_feedback_due_at", ""),
    }


@whitelist()
def get_job_offer_snapshot(job_offer: str) -> dict[str, Any]:
    if not frappe:
        raise RuntimeError("Frappe is required for fetching Job Offer snapshots.")

    offer = frappe.get_doc("Job Offer", job_offer)
    _assert_doc_permission(offer, "read")
    applicant = frappe.get_doc("Job Applicant", offer.job_applicant) if getattr(offer, "job_applicant", None) else None
    if applicant:
        _assert_doc_permission(applicant, "read")
    opening = _get_job_opening_doc(getattr(applicant, "job_title", None))
    if opening:
        _assert_doc_permission(opening, "read")
    screening = _get_latest_screening_doc(applicant.name if applicant else None)
    if screening:
        _assert_doc_permission(screening, "read")
    onboarding_name = frappe.db.get_value("Employee Onboarding", {"job_offer": offer.name}, "name")

    payroll_status = getattr(offer, "aihr_payroll_handoff_status", "") or "Not Started"
    next_action = get_offer_next_action(offer.status, payroll_status)
    salary_expectation = _format_salary_expectation(applicant)
    opening_salary_range = _format_opening_salary_range(opening)
    handoff_summary = build_offer_handoff_notes(
        candidate_name=getattr(applicant, "applicant_name", "") if applicant else "",
        opening_title=getattr(opening, "job_title", "") if opening else "",
        offer_status=offer.status,
        onboarding_owner=getattr(offer, "aihr_onboarding_owner", ""),
        payroll_handoff_status=payroll_status,
        salary_expectation=salary_expectation,
        compensation_notes=getattr(offer, "aihr_compensation_notes", ""),
    )
    payroll_handoff_summary = getattr(offer, "aihr_payroll_handoff_summary", "") or build_payroll_handoff_summary(
        candidate_name=getattr(applicant, "applicant_name", "") if applicant else "",
        opening_title=getattr(opening, "job_title", "") if opening else "",
        payroll_owner=getattr(offer, "aihr_payroll_owner", ""),
        payroll_handoff_status=payroll_status,
        salary_expectation=salary_expectation,
        opening_salary_range=opening_salary_range,
        compensation_notes=getattr(offer, "aihr_compensation_notes", ""),
    )

    return {
        "job_offer": {
            "name": offer.name,
            "status": offer.status,
            "offer_date": offer.offer_date,
            "designation": offer.designation,
            "company": offer.company,
            "onboarding_owner": getattr(offer, "aihr_onboarding_owner", ""),
            "payroll_owner": getattr(offer, "aihr_payroll_owner", ""),
            "payroll_handoff_status": payroll_status,
            "compensation_notes": getattr(offer, "aihr_compensation_notes", ""),
            "payroll_handoff_summary": payroll_handoff_summary,
            "terms_preview": _truncate_text(_strip_html(offer.terms or ""), 180),
        },
        "job_applicant": {
            "name": applicant.name,
            "applicant_name": applicant.applicant_name,
            "email_id": applicant.email_id,
            "phone_number": applicant.phone_number,
            "salary_expectation": salary_expectation,
            "aihr_match_score": getattr(applicant, "aihr_match_score", 0),
        }
        if applicant
        else None,
        "job_opening": {
            "name": opening.name,
            "job_title": opening.job_title,
        }
        if opening
        else None,
        "screening": {
            "status": screening.status,
            "ai_summary": screening.ai_summary,
            "strengths": _lines_to_list(screening.strengths),
            "risks": _lines_to_list(screening.risks),
        }
        if screening
        else None,
        "actions": {
            "next_action": next_action,
            "handoff_summary": handoff_summary,
            "payroll_handoff_summary": payroll_handoff_summary,
            "candidate_route": frappe.utils.get_url_to_form("Job Applicant", applicant.name) if applicant else "",
            "onboarding_route": frappe.utils.get_url_to_form("Employee Onboarding", onboarding_name) if onboarding_name else "",
        },
    }


@whitelist()
def prepare_job_offer_handoff(job_offer: str, save: int = 1) -> dict[str, Any]:
    if not frappe:
        raise RuntimeError("Frappe is required for preparing Job Offer handoff.")

    offer = frappe.get_doc("Job Offer", job_offer)
    applicant = frappe.get_doc("Job Applicant", offer.job_applicant) if getattr(offer, "job_applicant", None) else None
    opening = _get_job_opening_doc(getattr(applicant, "job_title", None))

    if not getattr(offer, "aihr_onboarding_owner", None):
        offer.aihr_onboarding_owner = _default_owner()
    if not getattr(offer, "aihr_payroll_owner", None):
        offer.aihr_payroll_owner = getattr(offer, "aihr_onboarding_owner", None) or _default_owner()
    if not getattr(offer, "aihr_payroll_handoff_status", None):
        offer.aihr_payroll_handoff_status = "Not Started"
    if not getattr(offer, "aihr_compensation_notes", None):
        offer.aihr_compensation_notes = _build_compensation_notes(applicant, opening)
    offer.aihr_payroll_handoff_summary = _build_payroll_handoff_summary(applicant, opening, offer)

    if save:
        offer.save(ignore_permissions=True)

    return {
        "job_offer": offer.name,
        "onboarding_owner": getattr(offer, "aihr_onboarding_owner", ""),
        "payroll_owner": getattr(offer, "aihr_payroll_owner", ""),
        "payroll_handoff_status": getattr(offer, "aihr_payroll_handoff_status", ""),
        "compensation_notes": getattr(offer, "aihr_compensation_notes", ""),
        "payroll_handoff_summary": getattr(offer, "aihr_payroll_handoff_summary", ""),
    }


@whitelist()
def mark_job_offer_payroll_ready(job_offer: str, save: int = 1) -> dict[str, Any]:
    if not frappe:
        raise RuntimeError("Frappe is required for updating Job Offer payroll handoff.")

    offer = frappe.get_doc("Job Offer", job_offer)
    applicant = frappe.get_doc("Job Applicant", offer.job_applicant) if getattr(offer, "job_applicant", None) else None
    opening = _get_job_opening_doc(getattr(applicant, "job_title", None))

    offer.aihr_payroll_handoff_status = "Ready"
    if not getattr(offer, "aihr_onboarding_owner", None):
        offer.aihr_onboarding_owner = _default_owner()
    if not getattr(offer, "aihr_payroll_owner", None):
        offer.aihr_payroll_owner = getattr(offer, "aihr_onboarding_owner", None) or _default_owner()
    offer.aihr_payroll_handoff_summary = _build_payroll_handoff_summary(applicant, opening, offer)

    onboarding_name = frappe.db.get_value("Employee Onboarding", {"job_offer": offer.name}, "name")
    if onboarding_name:
        onboarding = frappe.get_doc("Employee Onboarding", onboarding_name)
        onboarding.aihr_payroll_ready = 1
        if not getattr(onboarding, "aihr_employee_creation_status", None):
            onboarding.aihr_employee_creation_status = "Ready"
        onboarding.save(ignore_permissions=True)

    if save:
        offer.save(ignore_permissions=True)

    return {
        "job_offer": offer.name,
        "payroll_handoff_status": offer.aihr_payroll_handoff_status,
        "next_action": get_offer_next_action(offer.status, offer.aihr_payroll_handoff_status),
    }


@whitelist()
def complete_job_offer_payroll_handoff(job_offer: str, save: int = 1) -> dict[str, Any]:
    if not frappe:
        raise RuntimeError("Frappe is required for completing Job Offer payroll handoff.")

    offer = frappe.get_doc("Job Offer", job_offer)
    applicant = frappe.get_doc("Job Applicant", offer.job_applicant) if getattr(offer, "job_applicant", None) else None
    opening = _get_job_opening_doc(getattr(applicant, "job_title", None))

    if not getattr(offer, "aihr_onboarding_owner", None):
        offer.aihr_onboarding_owner = _default_owner()
    if not getattr(offer, "aihr_payroll_owner", None):
        offer.aihr_payroll_owner = getattr(offer, "aihr_onboarding_owner", None) or _default_owner()
    if not getattr(offer, "aihr_compensation_notes", None):
        offer.aihr_compensation_notes = _build_compensation_notes(applicant, opening)
    offer.aihr_payroll_handoff_status = "Completed"
    offer.aihr_payroll_handoff_summary = _build_payroll_handoff_summary(applicant, opening, offer)

    onboarding_name = frappe.db.get_value("Employee Onboarding", {"job_offer": offer.name}, "name")
    if onboarding_name:
        onboarding = frappe.get_doc("Employee Onboarding", onboarding_name)
        onboarding.aihr_payroll_ready = 1
        if getattr(onboarding, "aihr_employee_record", None):
            onboarding.aihr_employee_creation_status = "Completed"
        else:
            onboarding.aihr_employee_creation_status = "Ready"
        onboarding.save(ignore_permissions=True)

    if save:
        offer.save(ignore_permissions=True)

    return {
        "job_offer": offer.name,
        "payroll_handoff_status": offer.aihr_payroll_handoff_status,
        "payroll_handoff_summary": offer.aihr_payroll_handoff_summary,
        "next_action": get_payroll_handoff_next_action(offer.aihr_payroll_handoff_status),
    }


@whitelist()
def get_interview_feedback_blueprint(interview: str) -> dict[str, Any]:
    if not frappe:
        raise RuntimeError("Frappe is required for preparing Interview Feedback blueprints.")

    interview_doc = frappe.get_doc("Interview", interview)
    interviewer = _get_default_interviewer(interview_doc)
    skill_names = _get_interview_round_skill_names(interview_doc.interview_round)

    return {
        "interview": interview_doc.name,
        "interviewer": interviewer,
        "skill_assessment": [{"skill": skill_name, "rating": 3} for skill_name in skill_names],
        "next_step_suggestion": get_feedback_next_action("Cleared"),
        "hiring_recommendation": "Yes",
    }


@whitelist()
def get_interview_feedback_snapshot(interview_feedback: str) -> dict[str, Any]:
    if not frappe:
        raise RuntimeError("Frappe is required for fetching Interview Feedback snapshots.")

    feedback = frappe.get_doc("Interview Feedback", interview_feedback)
    _assert_doc_permission(feedback, "read")
    interview_doc = frappe.get_doc("Interview", feedback.interview) if getattr(feedback, "interview", None) else None
    if interview_doc:
        _assert_doc_permission(interview_doc, "read")
    applicant = frappe.get_doc("Job Applicant", feedback.job_applicant) if getattr(feedback, "job_applicant", None) else None
    if applicant:
        _assert_doc_permission(applicant, "read")
    opening = _get_job_opening_doc(
        (getattr(interview_doc, "job_opening", None) if interview_doc else None)
        or (getattr(applicant, "job_title", None) if applicant else None)
    )
    if opening:
        _assert_doc_permission(opening, "read")
    screening = _get_latest_screening_doc(applicant.name if applicant else None)
    if screening:
        _assert_doc_permission(screening, "read")

    rating_rows = [
        f"{row.skill}: {row.rating or '--'} / 5"
        for row in getattr(feedback, "skill_assessment", [])
        if getattr(row, "skill", None)
    ]
    average_rating = _calculate_average_rating(getattr(feedback, "skill_assessment", []))
    fallback_summary = build_feedback_summary(
        interviewer=getattr(feedback, "interviewer", ""),
        result=getattr(feedback, "result", ""),
        average_rating=f"{average_rating:.1f} / 5" if average_rating else "待补充",
        feedback=getattr(feedback, "feedback", ""),
        ratings=rating_rows,
    )
    summary = getattr(feedback, "aihr_feedback_summary", "") or getattr(interview_doc, "interview_summary", "") or fallback_summary

    return {
        "interview_feedback": {
            "name": feedback.name,
            "interview": feedback.interview,
            "interviewer": feedback.interviewer,
            "result": feedback.result,
            "feedback": feedback.feedback,
            "average_rating": average_rating,
            "hiring_recommendation": getattr(feedback, "aihr_hiring_recommendation", ""),
            "next_step_suggestion": getattr(feedback, "aihr_next_step_suggestion", "") or get_feedback_next_action(feedback.result),
        },
        "interview": {
            "name": interview_doc.name,
            "status": interview_doc.status,
            "interview_round": interview_doc.interview_round,
            "schedule_label": _build_interview_schedule_label(interview_doc),
        }
        if interview_doc
        else None,
        "job_applicant": {
            "name": applicant.name,
            "applicant_name": applicant.applicant_name,
            "aihr_match_score": getattr(applicant, "aihr_match_score", 0),
        }
        if applicant
        else None,
        "job_opening": {
            "name": opening.name,
            "job_title": opening.job_title,
        }
        if opening
        else None,
        "screening": {
            "ai_summary": screening.ai_summary,
            "strengths": _lines_to_list(screening.strengths),
            "risks": _lines_to_list(screening.risks),
        }
        if screening
        else None,
        "actions": {
            "summary": summary,
            "next_action": get_feedback_next_action(feedback.result),
            "interview_route": frappe.utils.get_url_to_form("Interview", interview_doc.name) if interview_doc else "",
        },
    }


@whitelist()
def apply_interview_feedback(interview_feedback: str, save: int = 1) -> dict[str, Any]:
    if not frappe:
        raise RuntimeError("Frappe is required for applying Interview Feedback.")

    feedback = frappe.get_doc("Interview Feedback", interview_feedback)
    if not getattr(feedback, "interview", None):
        frappe.throw("请先关联面试记录。")
    if not getattr(feedback, "result", None):
        frappe.throw("请先填写面试结论。")
    if not getattr(feedback, "interviewer", None):
        feedback.interviewer = _default_owner()
    if not getattr(feedback, "aihr_hiring_recommendation", None):
        feedback.aihr_hiring_recommendation = "Yes" if feedback.result == "Cleared" else "No"
    feedback.aihr_next_step_suggestion = get_feedback_next_action(feedback.result)

    if save and feedback.docstatus == 0:
        feedback.save(ignore_permissions=True)

    interview_doc = frappe.get_doc("Interview", feedback.interview)
    average_rating = _calculate_average_rating(getattr(feedback, "skill_assessment", []))
    fallback_summary = build_feedback_summary(
        interviewer=getattr(feedback, "interviewer", ""),
        result=getattr(feedback, "result", ""),
        average_rating=f"{average_rating:.1f} / 5" if average_rating else "待补充",
        feedback=getattr(feedback, "feedback", ""),
        ratings=[
            f"{row.skill}: {row.rating or '--'} / 5"
            for row in getattr(feedback, "skill_assessment", [])
            if getattr(row, "skill", None)
        ],
    )
    opening = _get_job_opening_doc(getattr(interview_doc, "job_opening", None))
    applicant = frappe.get_doc("Job Applicant", feedback.job_applicant) if getattr(feedback, "job_applicant", None) else None
    screening = _get_latest_screening_doc(applicant.name if applicant else None)
    ai_feedback = summarize_interview_feedback_with_llm(
        candidate_name=getattr(applicant, "applicant_name", "") if applicant else "",
        opening_title=getattr(opening, "job_title", "") if opening else "",
        interview_round=getattr(interview_doc, "interview_round", ""),
        feedback_result=getattr(feedback, "result", ""),
        feedback_text=getattr(feedback, "feedback", ""),
        rating_rows=[
            f"{row.skill}: {row.rating or '--'} / 5"
            for row in getattr(feedback, "skill_assessment", [])
            if getattr(row, "skill", None)
        ],
        screening_summary=getattr(screening, "ai_summary", "") if screening else "",
        fallback_summary=fallback_summary,
        default_next_action=feedback.aihr_next_step_suggestion,
        default_hiring_recommendation=getattr(feedback, "aihr_hiring_recommendation", "") or ("Yes" if feedback.result == "Cleared" else "No"),
    )
    feedback.aihr_hiring_recommendation = ai_feedback["hiring_recommendation"]
    feedback.aihr_next_step_suggestion = ai_feedback["next_step_suggestion"]
    if hasattr(feedback, "aihr_feedback_summary"):
        feedback.aihr_feedback_summary = ai_feedback["summary"]
    if save and feedback.docstatus == 0:
        feedback.save(ignore_permissions=True)

    interview_doc.status = feedback.result
    interview_doc.interview_summary = _truncate_text(_strip_html(ai_feedback["interview_summary"]), 140)
    interview_doc.save(ignore_permissions=True)

    return {
        "interview_feedback": feedback.name,
        "interview": interview_doc.name,
        "interview_status": interview_doc.status,
        "next_action": feedback.aihr_next_step_suggestion,
    }


@whitelist()
def create_employee_onboarding_from_offer(job_offer: str, save: int = 1) -> dict[str, Any]:
    if not frappe:
        raise RuntimeError("Frappe is required for creating Employee Onboarding.")

    offer = frappe.get_doc("Job Offer", job_offer)
    applicant = frappe.get_doc("Job Applicant", offer.job_applicant) if getattr(offer, "job_applicant", None) else None
    opening = _get_job_opening_doc(getattr(applicant, "job_title", None))
    existing = frappe.db.exists("Employee Onboarding", {"job_offer": offer.name})
    if existing:
        return {
            "employee_onboarding": existing,
            "created": False,
            "route": frappe.utils.get_url_to_form("Employee Onboarding", existing),
        }

    owner = getattr(offer, "aihr_onboarding_owner", None) or _default_owner()
    onboarding = frappe.new_doc("Employee Onboarding")
    onboarding.job_applicant = applicant.name if applicant else ""
    onboarding.job_offer = offer.name
    onboarding.company = offer.company or getattr(opening, "company", "")
    onboarding.employee_name = getattr(applicant, "applicant_name", "") if applicant else ""
    onboarding.department = getattr(opening, "department", "") or frappe.db.get_value("Department", {}, "name")
    onboarding.designation = offer.designation or getattr(opening, "designation", "")
    onboarding.date_of_joining = _default_joining_date(getattr(offer, "offer_date", None))
    onboarding.boarding_begins_on = _default_boarding_begins_on(onboarding.date_of_joining)
    onboarding.notify_users_by_email = 0
    onboarding.aihr_handoff_owner = owner
    onboarding.aihr_employee_creation_status = "Ready" if getattr(offer, "aihr_payroll_handoff_status", "") in {"Ready", "Completed"} else "Not Started"
    onboarding.aihr_payroll_ready = 1 if getattr(offer, "aihr_payroll_handoff_status", "") in {"Ready", "Completed"} else 0
    onboarding.aihr_preboarding_notes = _build_preboarding_notes(applicant, offer, opening)
    for activity in default_onboarding_activities(owner):
        onboarding.append("activities", activity)

    if save:
        onboarding.save(ignore_permissions=True)

    return {
        "employee_onboarding": onboarding.name,
        "created": True,
        "route": frappe.utils.get_url_to_form("Employee Onboarding", onboarding.name),
    }


@whitelist()
def get_employee_onboarding_snapshot(employee_onboarding: str) -> dict[str, Any]:
    if not frappe:
        raise RuntimeError("Frappe is required for fetching Employee Onboarding snapshots.")

    onboarding = frappe.get_doc("Employee Onboarding", employee_onboarding)
    applicant = frappe.get_doc("Job Applicant", onboarding.job_applicant) if getattr(onboarding, "job_applicant", None) else None
    offer = frappe.get_doc("Job Offer", onboarding.job_offer) if getattr(onboarding, "job_offer", None) else None
    opening = _get_job_opening_doc(getattr(applicant, "job_title", None))

    activity_titles = [row.activity_name for row in getattr(onboarding, "activities", []) if getattr(row, "activity_name", None)]
    summary = build_onboarding_summary(
        candidate_name=getattr(applicant, "applicant_name", "") if applicant else "",
        opening_title=getattr(opening, "job_title", "") if opening else "",
        handoff_owner=getattr(onboarding, "aihr_handoff_owner", ""),
        boarding_status=getattr(onboarding, "boarding_status", ""),
        payroll_ready=bool(getattr(onboarding, "aihr_payroll_ready", 0)),
        date_of_joining=str(getattr(onboarding, "date_of_joining", "") or ""),
        activities=activity_titles,
        preboarding_notes=getattr(onboarding, "aihr_preboarding_notes", ""),
    )

    return {
        "employee_onboarding": {
            "name": onboarding.name,
            "boarding_status": onboarding.boarding_status,
            "date_of_joining": onboarding.date_of_joining,
            "boarding_begins_on": onboarding.boarding_begins_on,
            "handoff_owner": getattr(onboarding, "aihr_handoff_owner", ""),
            "employee_record": getattr(onboarding, "aihr_employee_record", "") or getattr(onboarding, "employee", ""),
            "employee_creation_status": getattr(onboarding, "aihr_employee_creation_status", ""),
            "payroll_ready": bool(getattr(onboarding, "aihr_payroll_ready", 0)),
            "preboarding_notes": getattr(onboarding, "aihr_preboarding_notes", ""),
        },
        "job_applicant": {
            "name": applicant.name,
            "applicant_name": applicant.applicant_name,
        }
        if applicant
        else None,
        "job_offer": {
            "name": offer.name,
            "status": offer.status,
            "compensation_notes": getattr(offer, "aihr_compensation_notes", ""),
        }
        if offer
        else None,
        "job_opening": {
            "name": opening.name,
            "job_title": opening.job_title,
        }
        if opening
        else None,
        "activities": activity_titles,
        "actions": {
            "summary": summary,
            "next_action": get_onboarding_next_action(onboarding.boarding_status, bool(getattr(onboarding, "aihr_payroll_ready", 0))),
            "offer_route": frappe.utils.get_url_to_form("Job Offer", offer.name) if offer else "",
            "candidate_route": frappe.utils.get_url_to_form("Job Applicant", applicant.name) if applicant else "",
            "employee_route": frappe.utils.get_url_to_form("Employee", onboarding.employee) if getattr(onboarding, "employee", None) else "",
        },
    }


@whitelist()
def prepare_employee_onboarding(employee_onboarding: str, save: int = 1) -> dict[str, Any]:
    if not frappe:
        raise RuntimeError("Frappe is required for preparing Employee Onboarding.")

    onboarding = frappe.get_doc("Employee Onboarding", employee_onboarding)
    applicant = frappe.get_doc("Job Applicant", onboarding.job_applicant) if getattr(onboarding, "job_applicant", None) else None
    offer = frappe.get_doc("Job Offer", onboarding.job_offer) if getattr(onboarding, "job_offer", None) else None
    opening = _get_job_opening_doc(getattr(applicant, "job_title", None))

    if not getattr(onboarding, "aihr_handoff_owner", None):
        onboarding.aihr_handoff_owner = getattr(offer, "aihr_onboarding_owner", None) if offer else _default_owner()
    if not getattr(onboarding, "aihr_preboarding_notes", None):
        onboarding.aihr_preboarding_notes = _build_preboarding_notes(applicant, offer, opening)
    if not getattr(onboarding, "activities", None):
        for activity in default_onboarding_activities(onboarding.aihr_handoff_owner or _default_owner()):
            onboarding.append("activities", activity)
    if not getattr(onboarding, "aihr_employee_record", None) and getattr(onboarding, "employee", None):
        onboarding.aihr_employee_record = onboarding.employee
    if not getattr(onboarding, "aihr_payroll_ready", None) and offer:
        onboarding.aihr_payroll_ready = 1 if getattr(offer, "aihr_payroll_handoff_status", "") in {"Ready", "Completed"} else 0
    if getattr(onboarding, "aihr_employee_record", None):
        onboarding.aihr_employee_creation_status = "Completed"
    elif bool(getattr(onboarding, "aihr_payroll_ready", 0)):
        onboarding.aihr_employee_creation_status = "Ready"
    elif not getattr(onboarding, "aihr_employee_creation_status", None):
        onboarding.aihr_employee_creation_status = "Not Started"

    if save:
        onboarding.save(ignore_permissions=True)

    return {
        "employee_onboarding": onboarding.name,
        "handoff_owner": getattr(onboarding, "aihr_handoff_owner", ""),
        "employee_creation_status": getattr(onboarding, "aihr_employee_creation_status", ""),
        "employee_record": getattr(onboarding, "aihr_employee_record", ""),
        "payroll_ready": bool(getattr(onboarding, "aihr_payroll_ready", 0)),
        "activity_count": len(getattr(onboarding, "activities", [])),
    }


@whitelist()
def create_employee_from_onboarding(employee_onboarding: str, save: int = 1) -> dict[str, Any]:
    if not frappe:
        raise RuntimeError("Frappe is required for creating Employee records.")

    onboarding = frappe.get_doc("Employee Onboarding", employee_onboarding)
    applicant = frappe.get_doc("Job Applicant", onboarding.job_applicant) if getattr(onboarding, "job_applicant", None) else None
    offer = frappe.get_doc("Job Offer", onboarding.job_offer) if getattr(onboarding, "job_offer", None) else None

    existing_employee = getattr(onboarding, "aihr_employee_record", None) or getattr(onboarding, "employee", None)
    if existing_employee and frappe.db.exists("Employee", existing_employee):
        return {
            "employee": existing_employee,
            "created": False,
            "route": frappe.utils.get_url_to_form("Employee", existing_employee),
        }

    matched_employee = _find_existing_employee_for_onboarding(applicant, onboarding)
    if matched_employee:
        onboarding.aihr_employee_record = matched_employee
        onboarding.employee = matched_employee
        onboarding.aihr_employee_creation_status = "Completed"
        if save:
            onboarding.save(ignore_permissions=True)
        return {
            "employee": matched_employee,
            "created": False,
            "route": frappe.utils.get_url_to_form("Employee", matched_employee),
        }

    payload = _build_employee_payload(applicant, offer, onboarding)
    employee = frappe.get_doc({"doctype": "Employee", **payload})
    if save:
        employee.insert(ignore_permissions=True)

    onboarding = frappe.get_doc("Employee Onboarding", employee_onboarding)
    onboarding.employee = employee.name
    onboarding.aihr_employee_record = employee.name
    onboarding.aihr_employee_creation_status = "Completed"
    if onboarding.boarding_status == "Pending":
        onboarding.boarding_status = "In Process"
    if save:
        onboarding.save(ignore_permissions=True)

    if applicant:
        applicant = frappe.get_doc("Job Applicant", applicant.name)
        applicant.aihr_ai_status = "Hired"
        applicant.aihr_next_action = "确认员工档案与首月薪资信息"
        applicant.aihr_last_contact_at = frappe.utils.now_datetime()
        applicant.save(ignore_permissions=True)

    return {
        "employee": employee.name,
        "created": True,
        "route": frappe.utils.get_url_to_form("Employee", employee.name),
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
    opening = _get_job_opening_doc(getattr(applicant, "job_title", None))
    screening_gate = _get_opening_screening_gate(opening)
    if not screening_gate["ready"]:
        if save:
            _mark_applicant_pending_requirements(applicant, screening_gate["message"])
        return {
            "job_applicant": applicant.name,
            "parsed_resume": None,
            "screening": None,
            "screening_gate": screening_gate,
        }

    requirements = _get_job_requirements(applicant)
    preferred_skills = _get_requisition_field(applicant, "aihr_nice_to_have_skills")
    preferred_city = _get_requisition_field(applicant, "aihr_work_city") or _get_job_opening_field(applicant, "location")

    resume_text = getattr(applicant, "aihr_resume_text", "") or ""
    if not resume_text and getattr(applicant, "resume_attachment", None):
        resume_text = _extract_resume_text_from_attachment(applicant.resume_attachment)

    parsed_resume = parse_resume_text(resume_text)
    heuristic = screen_candidate(
        parsed_resume=parsed_resume,
        job_requirements=requirements,
        preferred_skills=preferred_skills or "",
        preferred_city=preferred_city or "",
    )
    screening = enhance_screening_with_llm(
        parsed_resume=parsed_resume,
        resume_text=resume_text,
        opening_title=build_opening_display_title(opening) if opening else "",
        job_requirements=requirements,
        preferred_skills=preferred_skills or "",
        preferred_city=preferred_city or "",
        heuristic_screening=heuristic,
    )

    if save:
        _upsert_ai_screening(applicant, parsed_resume, screening)
        _update_applicant_summary(applicant, parsed_resume, screening, resume_text)

    return {
        "job_applicant": applicant.name,
        "parsed_resume": parsed_resume,
        "screening": screening,
        "screening_gate": screening_gate,
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
    completed = [item for item in screened if item.get("screening")]
    skipped = [item for item in screened if not item.get("screening")]

    return {
        "job_opening": job_opening,
        "screened_count": len(completed),
        "skipped_count": len(skipped),
        "job_applicants": [item["job_applicant"] for item in completed],
        "screening_gate": skipped[0].get("screening_gate") if skipped else None,
    }


def _build_interviewer_pack_for_context(interview_doc, applicant, opening, screening) -> str:
    fallback_pack = build_interviewer_pack(
        candidate_name=getattr(applicant, "applicant_name", "") if applicant else "",
        opening_title=getattr(opening, "job_title", "") if opening else "",
        interview_round=getattr(interview_doc, "interview_round", ""),
        interview_mode=_interview_mode_label(getattr(interview_doc, "aihr_interview_mode", "")),
        schedule_label=_build_interview_schedule_label(interview_doc),
        ai_summary=getattr(screening, "ai_summary", "") if screening else "",
        strengths=_lines_to_list(getattr(screening, "strengths", "")) if screening else [],
        risks=_lines_to_list(getattr(screening, "risks", "")) if screening else [],
        suggested_questions=_lines_to_list(getattr(screening, "suggested_questions", "")) if screening else [],
    )
    return build_interviewer_pack_with_llm(
        fallback_pack=fallback_pack,
        candidate_name=getattr(applicant, "applicant_name", "") if applicant else "",
        opening_title=getattr(opening, "job_title", "") if opening else "",
        interview_round=getattr(interview_doc, "interview_round", ""),
        interview_mode=_interview_mode_label(getattr(interview_doc, "aihr_interview_mode", "")),
        schedule_label=_build_interview_schedule_label(interview_doc),
        screening_summary=getattr(screening, "ai_summary", "") if screening else "",
        strengths=_lines_to_list(getattr(screening, "strengths", "")) if screening else [],
        risks=_lines_to_list(getattr(screening, "risks", "")) if screening else [],
        suggested_questions=_lines_to_list(getattr(screening, "suggested_questions", "")) if screening else [],
    )


def _get_default_interviewer(interview_doc) -> str:
    interviewers = [row.interviewer for row in getattr(interview_doc, "interview_details", []) if getattr(row, "interviewer", None)]
    if interviewers:
        return interviewers[0]
    if getattr(interview_doc, "aihr_follow_up_owner", None):
        return interview_doc.aihr_follow_up_owner
    return _default_owner()


def _get_interview_round_skill_names(interview_round: str | None) -> list[str]:
    if not interview_round or not frappe.db.exists("Interview Round", interview_round):
        return []
    round_doc = frappe.get_doc("Interview Round", interview_round)
    return [row.skill for row in getattr(round_doc, "expected_skill_set", []) if getattr(row, "skill", None)]


def _calculate_average_rating(rows) -> float:
    ratings = [float(row.rating) for row in (rows or []) if getattr(row, "rating", None)]
    if not ratings:
        return 0
    return round(sum(ratings) / len(ratings), 1)


def _get_latest_screening_doc(job_applicant: str | None):
    if not job_applicant:
        return None

    screening_names = frappe.get_all(
        "AI Screening",
        filters={"job_applicant": job_applicant},
        pluck="name",
        order_by="modified desc",
        limit_page_length=1,
    )
    return frappe.get_doc("AI Screening", screening_names[0]) if screening_names else None


def _get_job_opening_doc(job_opening: str | None):
    if not job_opening:
        return None
    if not frappe.db.exists("Job Opening", job_opening):
        return None
    return frappe.get_doc("Job Opening", job_opening)


def _assert_doc_permission(doc, permission_type: str = "read") -> None:
    if not doc:
        return
    if not doc.has_permission(permission_type):
        frappe.throw("你没有权限访问该记录。", frappe.PermissionError)


def _default_owner() -> str:
    session_user = getattr(frappe.session, "user", None)
    if session_user and session_user != "Guest":
        return session_user
    return "Administrator"


def _default_feedback_due_at(scheduled_on) -> str:
    from frappe.utils import add_to_date, get_datetime

    if not scheduled_on:
        return ""
    due_date = add_to_date(scheduled_on, days=1)
    return get_datetime(f"{due_date} 12:00:00")


def _build_interview_schedule_label(interview_doc) -> str:
    from frappe.utils import format_date, format_time

    parts = []
    if getattr(interview_doc, "scheduled_on", None):
        parts.append(format_date(interview_doc.scheduled_on))
    time_bits = []
    if getattr(interview_doc, "from_time", None):
        time_bits.append(format_time(interview_doc.from_time))
    if getattr(interview_doc, "to_time", None):
        time_bits.append(format_time(interview_doc.to_time))
    if time_bits:
        parts.append(" - ".join(time_bits))
    return " ".join(parts).strip()


def _format_datetime_label(value) -> str:
    from frappe.utils import format_datetime

    if not value:
        return ""
    return format_datetime(value)


def _format_salary_expectation(applicant) -> str:
    if not applicant:
        return "待补充"
    currency = getattr(applicant, "currency", "") or ""
    lower = getattr(applicant, "lower_range", None)
    upper = getattr(applicant, "upper_range", None)
    if not lower and not upper:
        return "待补充"
    lower_text = _format_amount(lower) if lower else "--"
    if upper:
        return f"{currency} {lower_text} - {_format_amount(upper)}".strip()
    return f"{currency} {lower_text}".strip()


def _build_compensation_notes(applicant, opening) -> str:
    expectation = _format_salary_expectation(applicant)
    opening_range = _format_opening_salary_range(opening)
    candidate_name = getattr(applicant, "applicant_name", "候选人") if applicant else "候选人"
    return (
        f"{candidate_name} 当前期望 {expectation}；岗位预算 {opening_range}。"
        " 建议确认 base、试用期薪资、到岗时间和补贴项后，再推进入职与薪酬建档。"
    )


def _format_opening_salary_range(opening) -> str:
    if not opening:
        return "待补充"
    currency = getattr(opening, "currency", "") or ""
    lower = getattr(opening, "lower_range", None)
    upper = getattr(opening, "upper_range", None)
    if not lower and not upper:
        return "待补充"
    lower_text = _format_amount(lower) if lower else "--"
    if upper:
        return f"{currency} {lower_text} - {_format_amount(upper)}".strip()
    return f"{currency} {lower_text}".strip()


def _interview_mode_label(value: str | None) -> str:
    labels = {
        "Phone": "电话",
        "Video": "视频",
        "Onsite": "现场",
    }
    return labels.get(value or "", value or "待确认")


def _format_amount(value: Any) -> str:
    numeric = float(value)
    if numeric.is_integer():
        return str(int(numeric))
    return f"{numeric:.2f}"


def _default_joining_date(base_date) -> str:
    from frappe.utils import add_to_date, today

    anchor = base_date or today()
    return add_to_date(anchor, days=14)


def _default_boarding_begins_on(joining_date) -> str:
    from frappe.utils import add_to_date

    if not joining_date:
        return ""
    return add_to_date(joining_date, days=-7)


def _build_preboarding_notes(applicant, offer, opening) -> str:
    candidate_name = getattr(applicant, "applicant_name", "候选人") if applicant else "候选人"
    job_title = getattr(opening, "job_title", "") if opening else getattr(offer, "designation", "")
    compensation = getattr(offer, "aihr_compensation_notes", "") if offer else ""
    return (
        f"{candidate_name} 的岗位为 {job_title or '待补充'}。"
        f" {compensation or '请确认入职资料、设备准备和薪酬建档信息。'}"
    ).strip()


def _build_payroll_handoff_summary(applicant, opening, offer) -> str:
    return build_payroll_handoff_summary(
        candidate_name=getattr(applicant, "applicant_name", "") if applicant else "",
        opening_title=getattr(opening, "job_title", "") if opening else getattr(offer, "designation", ""),
        payroll_owner=getattr(offer, "aihr_payroll_owner", ""),
        payroll_handoff_status=getattr(offer, "aihr_payroll_handoff_status", "") or "Not Started",
        salary_expectation=_format_salary_expectation(applicant),
        opening_salary_range=_format_opening_salary_range(opening),
        compensation_notes=getattr(offer, "aihr_compensation_notes", ""),
    )


def _build_employee_payload(applicant, offer, onboarding) -> dict[str, Any]:
    employee_name = (
        getattr(onboarding, "employee_name", None)
        or getattr(applicant, "applicant_name", None)
        or "AIHR Employee"
    )
    first_name, middle_name, last_name = split_person_name(employee_name)
    email_id = getattr(applicant, "email_id", "") if applicant else ""
    joining_date = getattr(onboarding, "date_of_joining", None)
    gender_name = _get_default_gender_name()
    date_of_birth = _default_employee_birth_date()
    payload = {
        "naming_series": "HR-EMP-",
        "first_name": first_name,
        "middle_name": middle_name,
        "last_name": last_name,
        "company": getattr(onboarding, "company", None) or getattr(offer, "company", ""),
        "department": getattr(onboarding, "department", ""),
        "designation": getattr(onboarding, "designation", "") or getattr(offer, "designation", ""),
        "date_of_joining": joining_date,
        "status": resolve_employee_status(joining_date),
        "gender": gender_name,
        "date_of_birth": date_of_birth,
        "personal_email": email_id or None,
        "company_email": email_id or None,
        "prefered_contact_email": "Personal Email" if email_id else "",
    }
    if email_id and frappe.db.exists("User", email_id):
        payload["user_id"] = email_id
    return payload


def _find_existing_employee_for_onboarding(applicant, onboarding) -> str | None:
    email_id = getattr(applicant, "email_id", "") if applicant else ""
    if email_id:
        for fieldname in ("personal_email", "company_email", "user_id"):
            employee_name = frappe.db.get_value("Employee", {fieldname: email_id}, "name")
            if employee_name:
                return employee_name

    employee_name = getattr(onboarding, "employee_name", "") or getattr(applicant, "applicant_name", "")
    if employee_name and getattr(onboarding, "company", None):
        return frappe.db.get_value(
            "Employee",
            {"employee_name": employee_name, "company": onboarding.company},
            "name",
        )

    return None


def _get_default_gender_name() -> str:
    preferred_names = ("Not Specified", "Prefer not to say", "Unknown", "Female", "Male")
    for name in preferred_names:
        if frappe.db.exists("Gender", name):
            return name
    gender_name = frappe.db.get_value("Gender", {}, "name")
    if gender_name:
        return gender_name
    gender = frappe.get_doc({"doctype": "Gender", "gender": "Not Specified"})
    gender.insert(ignore_permissions=True)
    return gender.name


def _default_employee_birth_date() -> str:
    return "1990-01-01"


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

    try:
        file_path = _resolve_file_url_to_path(file_url)
    except FileNotFoundError:
        return ""
    return extract_text_from_file(file_path)


def _resolve_file_url_to_path(file_url: str) -> Path:
    if not file_url:
        raise FileNotFoundError("Missing file URL.")

    site_path = Path(frappe.get_site_path())
    relative_path = file_url.lstrip("/")
    candidates = [
        site_path / relative_path,
        site_path / "public" / "files" / Path(file_url).name,
        site_path / "private" / "files" / Path(file_url).name,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"File not found for URL: {file_url}")


def _upsert_job_applicant_from_archive_item(
    opening,
    batch_reference: str,
    supplier_name: str,
    source_channel: str,
    archive_item: dict[str, Any],
):
    from frappe.utils.file_manager import save_file

    parsed_resume = archive_item.get("parsed_resume") or {}
    email = (parsed_resume.get("emails") or [""])[0]
    phone = (parsed_resume.get("phones") or [""])[0]
    parsed_name = str(parsed_resume.get("name") or "").strip()
    applicant_name = (
        parsed_name
        if is_valid_name(parsed_name)
        else infer_name_from_file_name(archive_item["file_name"]) or Path(archive_item["file_name"]).stem
    )
    if not email:
        email = _fallback_resume_email(archive_item["file_name"], applicant_name, phone, batch_reference)

    applicant = _find_existing_job_applicant(opening.name, email, phone, applicant_name)
    created = applicant is None
    if not applicant:
        applicant = frappe.new_doc("Job Applicant")
        applicant.job_title = opening.name
        applicant.status = "Open"

    applicant.applicant_name = applicant_name
    applicant.email_id = email or getattr(applicant, "email_id", "")
    applicant.phone_number = phone or getattr(applicant, "phone_number", "")
    applicant.country = getattr(applicant, "country", "") or "China"
    applicant.aihr_resume_text = archive_item.get("resume_text", "")
    applicant.aihr_resume_file_name = archive_item["file_name"]
    applicant.aihr_resume_source_supplier = supplier_name
    applicant.aihr_resume_source_channel = source_channel
    applicant.aihr_resume_intake_batch = batch_reference
    applicant.aihr_resume_parse_status = archive_item.get("status") or "Parsed"
    if not getattr(applicant, "aihr_ai_status", None):
        applicant.aihr_ai_status = "Not Screened"
    try:
        frappe.flags.aihr_skip_auto_screening = True
        applicant.save(ignore_permissions=True)

        saved_file = save_file(
            archive_item["file_name"],
            archive_item.get("content", b""),
            applicant.doctype,
            applicant.name,
            is_private=1,
            df="resume_attachment",
        )
        applicant.resume_attachment = saved_file.file_url
        applicant.save(ignore_permissions=True)
    finally:
        frappe.flags.aihr_skip_auto_screening = False

    return applicant, created


def _fallback_resume_email(file_name: str, applicant_name: str, phone: str, batch_reference: str) -> str:
    if phone:
        return f"resume-{phone}@aihr.local"

    basis = f"{file_name}|{applicant_name}|{batch_reference}"
    digest = sha1(basis.encode("utf-8", errors="ignore")).hexdigest()[:12]
    return f"resume-{digest}@aihr.local"


def _find_existing_job_applicant(job_opening: str, email: str, phone: str, applicant_name: str):
    if email:
        existing = frappe.db.exists("Job Applicant", {"email_id": email})
        if existing:
            return frappe.get_doc("Job Applicant", existing)

    if phone:
        existing = frappe.db.exists("Job Applicant", {"job_title": job_opening, "phone_number": phone})
        if existing:
            return frappe.get_doc("Job Applicant", existing)

    if applicant_name:
        existing = frappe.db.exists(
            "Job Applicant",
            {"job_title": job_opening, "applicant_name": applicant_name},
        )
        if existing:
            return frappe.get_doc("Job Applicant", existing)

    return None


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


def _mark_applicant_pending_requirements(applicant, message: str) -> None:
    applicant.aihr_ai_status = "Not Screened"
    applicant.aihr_next_action = "先完善岗位需求，再运行 AI 初筛"
    if not getattr(applicant, "aihr_match_score", None):
        applicant.aihr_match_score = 0
    applicant.save(ignore_permissions=True)


def _get_opening_screening_gate(opening) -> dict[str, Any]:
    if not opening:
        return {
            "ready": False,
            "opening_title": "未关联岗位",
            "missing_fields": ["招聘中岗位"],
            "message": "候选人尚未关联招聘中岗位，暂不能进行 AI 初筛。",
        }

    requisition = (
        frappe.get_doc("Job Requisition", opening.job_requisition)
        if getattr(opening, "job_requisition", None)
        else None
    )
    payload = {
        "job_title": build_opening_display_title(opening),
        "designation": getattr(opening, "designation", "") or (getattr(requisition, "designation", "") if requisition else ""),
        "job_requisition": getattr(opening, "job_requisition", ""),
        "description": getattr(opening, "description", "") or (getattr(requisition, "description", "") if requisition else ""),
        "aihr_must_have_skills": getattr(requisition, "aihr_must_have_skills", "") if requisition else "",
    }
    return evaluate_screening_readiness(payload)


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


def _opening_title_by_name(opening_by_name: dict[str, dict[str, Any]], opening_name: str | None) -> str:
    if not opening_name:
        return "未关联岗位"
    opening = opening_by_name.get(opening_name) or {}
    return build_opening_display_title(opening) if opening else opening_name


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


def _strip_html(value: str) -> str:
    import re

    plain = re.sub(r"<[^>]+>", " ", value or "")
    return " ".join(plain.split())
