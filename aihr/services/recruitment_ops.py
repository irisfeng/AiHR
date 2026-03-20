from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from aihr.services.screening import build_agency_brief


def generate_requisition_agency_brief(source: Mapping[str, Any] | Any) -> str:
    return build_agency_brief(build_requisition_payload(source))


def build_requisition_payload(source: Mapping[str, Any] | Any) -> dict[str, Any]:
    return {
        "job_title": _read(source, "job_title") or _read(source, "designation") or "New Role",
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


def get_screening_next_action(recommended_status: str) -> str:
    mapping = {
        "Advance": "安排经理初筛",
        "Ready for Review": "经理复核候选人摘要",
        "Hold": "补充信息或暂缓推进",
        "Reject": "确认是否淘汰",
    }
    return mapping.get(recommended_status, "经理初筛")


def _read(source: Mapping[str, Any] | Any, fieldname: str) -> Any:
    if isinstance(source, Mapping):
        return source.get(fieldname)
    return getattr(source, fieldname, None)
