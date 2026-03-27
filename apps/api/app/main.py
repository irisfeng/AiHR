from __future__ import annotations

import json
import sqlite3
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from aihr.services.recruitment_ops import (
    build_requisition_payload,
    generate_requisition_agency_brief,
    get_screening_next_action,
)
from aihr.services.screening import screen_candidate

from .store import (
    apply_interview_feedback,
    bootstrap_database,
    create_candidate,
    create_interview,
    create_job,
    create_offer,
    get_app_state,
    get_database_path,
    get_db,
    list_candidate_timeline,
    list_candidates,
    list_interviews,
    list_jobs,
    list_offers,
    load_demo_seed,
    mark_offer_payroll_ready,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    bootstrap_database()
    yield


app = FastAPI(
    title="AIHR Recruit API",
    summary="Standalone recruiting API for the direct rebuild track.",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ScreeningPreviewRequest(BaseModel):
    name: str = ""
    city: str = ""
    skills: list[str] = Field(default_factory=list)
    years_of_experience: float = 0
    requirements: str
    preferred_skills: str = ""
    preferred_city: str = ""


class AgencyBriefRequest(BaseModel):
    job_title: str = ""
    designation: str = ""
    department: str = ""
    aihr_work_city: str = ""
    aihr_work_mode: str = ""
    aihr_work_schedule: str = ""
    aihr_salary_currency: str = "CNY"
    aihr_salary_min: str = ""
    aihr_salary_max: str = ""
    aihr_must_have_skills: str = ""
    aihr_nice_to_have_skills: str = ""
    reason_for_requesting: str = ""


class CandidateCreateRequest(BaseModel):
    name: str
    role: str
    city: str = ""
    experience: str = ""
    owner: str = ""
    source: str = "手动录入"
    status: str = "待经理复核"
    next_action: str = "运行 AI 初筛"
    score: int = 60
    skills: list[str] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)


class JobCreateRequest(BaseModel):
    title: str
    team: str = ""
    location: str = ""
    mode: str = "Hybrid"
    headcount: int = 1
    stage: str = "开放招聘"
    owner: str = ""
    urgency: str = "medium"
    summary: str = ""
    skills: list[str] = Field(default_factory=list)


class InterviewCreateRequest(BaseModel):
    candidate_name: str
    role: str
    round: str = "技术一面"
    mode: str = "视频"
    time_label: str = ""
    interviewer: str = ""
    status: str = "已安排"
    decision_window: str = "面试后 24 小时"
    pack_status: str = "待补充"
    summary: str = ""


class InterviewFeedbackRequest(BaseModel):
    decision: str
    summary: str
    strengths: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    next_step: str = ""
    actor: str = ""


class OfferCreateRequest(BaseModel):
    candidate_id: str
    job_id: str
    status: str = "Accepted"
    salary_expectation: str = ""
    compensation_notes: str = ""
    onboarding_owner: str = ""
    payroll_owner: str = ""
    payroll_handoff_status: str = "Not Started"


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "database": str(get_database_path())}


@app.get("/api/overview")
def get_overview(connection: sqlite3.Connection = Depends(get_db)) -> dict[str, Any]:
    seed = load_demo_seed()["overview"]
    jobs = list_jobs(connection)
    candidates = list_candidates(connection)
    interviews = list_interviews(connection)

    advancing_candidates = [item for item in candidates if item["score"] >= 80 or item["status"] in {"建议推进", "面试中"}]
    pending_feedback = [item for item in interviews if item["status"] == "待反馈"]
    live_offers = sum(int(item["offers"]) for item in jobs)
    review_count = len([item for item in candidates if item["status"] == "待经理复核"])
    active_interviews = len([item for item in interviews if item["status"] in {"待进行", "已安排", "待反馈"}])

    focus = get_app_state(connection, "overview_focus", seed["focus"])
    priorities = [
        {
            "title": item["title"],
            "detail": item["summary"],
            "tag": {"critical": "急招", "high": "优先", "medium": "常规"}.get(item["urgency"], "常规"),
        }
        for item in jobs[:3]
    ]

    pass_ratio = f"{round((len(advancing_candidates) / max(len(candidates), 1)) * 100)}% 实时通过率"

    return {
        "title": get_app_state(connection, "overview_title", seed["title"]),
        "subtitle": get_app_state(connection, "overview_subtitle", seed["subtitle"]),
        "stats": [
            {
                "label": "候选人池",
                "value": str(len(candidates)),
                "delta": "实时入库",
                "tone": "accent",
            },
            {
                "label": "通过初筛",
                "value": str(len(advancing_candidates)),
                "delta": pass_ratio,
                "tone": "positive",
            },
            {
                "label": "待收反馈",
                "value": str(len(pending_feedback)),
                "delta": "面试协同待闭环",
                "tone": "warning",
            },
            {
                "label": "Offer 推进中",
                "value": str(live_offers),
                "delta": "来自岗位漏斗",
                "tone": "neutral",
            },
        ],
        "pipeline": [
            {
                "label": "新需求",
                "count": len([item for item in jobs if item["urgency"] in {"critical", "high"}]),
            },
            {"label": "开放岗位", "count": len(jobs)},
            {"label": "AI 初筛", "count": len(candidates)},
            {"label": "经理复核", "count": review_count},
            {"label": "面试推进", "count": active_interviews},
            {"label": "Offer", "count": live_offers},
        ],
        "focus": focus,
        "priorities": priorities,
    }


@app.get("/api/jobs")
def get_jobs(connection: sqlite3.Connection = Depends(get_db)) -> list[dict[str, Any]]:
    return list_jobs(connection)


@app.post("/api/jobs", status_code=status.HTTP_201_CREATED)
def post_job(payload: JobCreateRequest, connection: sqlite3.Connection = Depends(get_db)) -> dict[str, Any]:
    return create_job(connection, payload.model_dump())


@app.get("/api/candidates")
def get_candidates(connection: sqlite3.Connection = Depends(get_db)) -> list[dict[str, Any]]:
    return list_candidates(connection)


@app.get("/api/candidates/{candidate_id}/timeline")
def get_candidate_timeline(candidate_id: str, connection: sqlite3.Connection = Depends(get_db)) -> list[dict[str, Any]]:
    return list_candidate_timeline(connection, candidate_id)


@app.post("/api/candidates", status_code=status.HTTP_201_CREATED)
def post_candidate(payload: CandidateCreateRequest, connection: sqlite3.Connection = Depends(get_db)) -> dict[str, Any]:
    return create_candidate(connection, payload.model_dump())


@app.get("/api/interviews")
def get_interviews(connection: sqlite3.Connection = Depends(get_db)) -> list[dict[str, Any]]:
    return list_interviews(connection)


@app.post("/api/interviews", status_code=status.HTTP_201_CREATED)
def post_interview(payload: InterviewCreateRequest, connection: sqlite3.Connection = Depends(get_db)) -> dict[str, Any]:
    return create_interview(connection, payload.model_dump())


@app.post("/api/interviews/{interview_id}/feedback")
def post_interview_feedback(
    interview_id: str,
    payload: InterviewFeedbackRequest,
    connection: sqlite3.Connection = Depends(get_db),
) -> dict[str, Any]:
    try:
        return apply_interview_feedback(connection, interview_id, payload.model_dump())
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@app.get("/api/offers")
def get_offers(connection: sqlite3.Connection = Depends(get_db)) -> list[dict[str, Any]]:
    return list_offers(connection)


@app.post("/api/offers", status_code=status.HTTP_201_CREATED)
def post_offer(payload: OfferCreateRequest, connection: sqlite3.Connection = Depends(get_db)) -> dict[str, Any]:
    try:
        return create_offer(connection, payload.model_dump())
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@app.post("/api/offers/{offer_id}/payroll-ready")
def post_offer_payroll_ready(offer_id: str, connection: sqlite3.Connection = Depends(get_db)) -> dict[str, Any]:
    try:
        return mark_offer_payroll_ready(connection, offer_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@app.post("/api/screening/preview")
def preview_screening(payload: ScreeningPreviewRequest) -> dict[str, Any]:
    parsed_resume = {
        "name": payload.name,
        "city": payload.city,
        "skills": payload.skills,
        "years_of_experience": payload.years_of_experience,
        "emails": ["demo@aihr.local"],
        "phones": ["13800000000"],
    }
    result = screen_candidate(
        parsed_resume=parsed_resume,
        job_requirements=payload.requirements,
        preferred_skills=payload.preferred_skills,
        preferred_city=payload.preferred_city,
    )
    result["next_action"] = get_screening_next_action(result["recommended_status"])
    return result


@app.post("/api/requisitions/agency-brief")
def preview_agency_brief(payload: AgencyBriefRequest) -> dict[str, Any]:
    body = payload.model_dump()
    return {
        "payload": build_requisition_payload(body),
        "brief": generate_requisition_agency_brief(body),
    }


@app.get("/api/debug/seed")
def debug_seed() -> dict[str, Any]:
    return json.loads(json.dumps(load_demo_seed(), ensure_ascii=False))
