from __future__ import annotations

import json
import os
import sqlite3
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from aihr.services.recruitment_ops import (
    build_offer_handoff_notes,
    build_payroll_handoff_summary,
    get_screening_next_action,
    get_offer_next_action,
)
from aihr.services.resume_intake import extract_resume_archive
from aihr.services.screening import screen_candidate

DEMO_DATA_FILE = Path(__file__).resolve().parents[2] / "shared" / "demo-data.json"
DEFAULT_DATABASE_PATH = Path(__file__).resolve().parents[1] / "data" / "aihr.sqlite3"
DEFAULT_INTAKE_ARCHIVE_DIR = Path(__file__).resolve().parents[1] / "data" / "resume_intake"
DATABASE_PATH_OVERRIDE: Path | None = None


def load_demo_seed() -> dict[str, Any]:
    return json.loads(DEMO_DATA_FILE.read_text(encoding="utf-8"))


def get_database_path() -> Path:
    if DATABASE_PATH_OVERRIDE is not None:
        return DATABASE_PATH_OVERRIDE
    return Path(os.getenv("AIHR_API_DATABASE_PATH") or DEFAULT_DATABASE_PATH)


def set_database_path(path: str | Path | None) -> None:
    global DATABASE_PATH_OVERRIDE
    DATABASE_PATH_OVERRIDE = Path(path) if path else None


def connect_db() -> sqlite3.Connection:
    database_path = get_database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    return connection


@contextmanager
def db_session() -> Iterator[sqlite3.Connection]:
    connection = connect_db()
    try:
        yield connection
    finally:
        connection.close()


def get_db() -> Iterator[sqlite3.Connection]:
    with db_session() as connection:
        yield connection


def bootstrap_database() -> None:
    with db_session() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS app_state (
                key TEXT PRIMARY KEY,
                value_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                team TEXT NOT NULL,
                location TEXT NOT NULL,
                mode TEXT NOT NULL,
                headcount INTEGER NOT NULL,
                stage TEXT NOT NULL,
                updated_at_label TEXT NOT NULL,
                applicants INTEGER NOT NULL,
                screened INTEGER NOT NULL,
                interviews INTEGER NOT NULL,
                offers INTEGER NOT NULL,
                owner TEXT NOT NULL,
                urgency TEXT NOT NULL,
                summary TEXT NOT NULL,
                skills_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS candidates (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                score INTEGER NOT NULL,
                status TEXT NOT NULL,
                city TEXT NOT NULL,
                experience TEXT NOT NULL,
                owner TEXT NOT NULL,
                source TEXT NOT NULL,
                next_action TEXT NOT NULL,
                skills_json TEXT NOT NULL,
                highlights_json TEXT NOT NULL,
                risks_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS interviews (
                id TEXT PRIMARY KEY,
                candidate_name TEXT NOT NULL,
                role TEXT NOT NULL,
                round TEXT NOT NULL,
                mode TEXT NOT NULL,
                time_label TEXT NOT NULL,
                interviewer TEXT NOT NULL,
                status TEXT NOT NULL,
                decision_window TEXT NOT NULL,
                pack_status TEXT NOT NULL,
                summary TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS interview_feedbacks (
                id TEXT PRIMARY KEY,
                interview_id TEXT NOT NULL UNIQUE,
                decision TEXT NOT NULL,
                summary TEXT NOT NULL,
                strengths_json TEXT NOT NULL,
                concerns_json TEXT NOT NULL,
                next_step TEXT NOT NULL,
                actor TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS candidate_timeline_events (
                id TEXT PRIMARY KEY,
                candidate_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                title TEXT NOT NULL,
                detail TEXT NOT NULL,
                actor TEXT NOT NULL,
                happened_at_label TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS offers (
                id TEXT PRIMARY KEY,
                candidate_id TEXT NOT NULL,
                job_id TEXT NOT NULL,
                candidate_name TEXT NOT NULL,
                opening_title TEXT NOT NULL,
                status TEXT NOT NULL,
                onboarding_owner TEXT NOT NULL,
                payroll_owner TEXT NOT NULL,
                payroll_handoff_status TEXT NOT NULL,
                salary_expectation TEXT NOT NULL,
                compensation_notes TEXT NOT NULL,
                handoff_summary TEXT NOT NULL,
                payroll_handoff_summary TEXT NOT NULL,
                next_action TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS resume_intake_jobs (
                id TEXT PRIMARY KEY,
                archive_name TEXT NOT NULL,
                archive_path TEXT NOT NULL,
                job_id TEXT NOT NULL,
                job_title TEXT NOT NULL,
                owner TEXT NOT NULL,
                source_label TEXT NOT NULL,
                status TEXT NOT NULL,
                total_files INTEGER NOT NULL,
                parsed_count INTEGER NOT NULL,
                unsupported_count INTEGER NOT NULL,
                failed_count INTEGER NOT NULL,
                created_candidate_count INTEGER NOT NULL,
                error_message TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS resume_intake_items (
                id TEXT PRIMARY KEY,
                intake_job_id TEXT NOT NULL,
                file_name TEXT NOT NULL,
                file_extension TEXT NOT NULL,
                status TEXT NOT NULL,
                reason TEXT NOT NULL,
                parser_engine TEXT NOT NULL,
                parsed_resume_json TEXT NOT NULL,
                candidate_id TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        seed_if_empty(connection)
        connection.commit()


def seed_if_empty(connection: sqlite3.Connection) -> None:
    seed = load_demo_seed()
    now = _now_iso()

    if _table_count(connection, "jobs") == 0:
        connection.executemany(
            """
            INSERT INTO jobs (
                id, title, team, location, mode, headcount, stage, updated_at_label,
                applicants, screened, interviews, offers, owner, urgency, summary,
                skills_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    item["id"],
                    item["title"],
                    item["team"],
                    item["location"],
                    item["mode"],
                    item["headcount"],
                    item["stage"],
                    item["updatedAt"],
                    item["applicants"],
                    item["screened"],
                    item["interviews"],
                    item["offers"],
                    item["owner"],
                    item["urgency"],
                    item["summary"],
                    _json_dump(item["skills"]),
                    now,
                    now,
                )
                for item in seed["jobs"]
            ],
        )

    if _table_count(connection, "candidates") == 0:
        connection.executemany(
            """
            INSERT INTO candidates (
                id, name, role, score, status, city, experience, owner, source,
                next_action, skills_json, highlights_json, risks_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    item["id"],
                    item["name"],
                    item["role"],
                    item["score"],
                    item["status"],
                    item["city"],
                    item["experience"],
                    item["owner"],
                    item["source"],
                    item["nextAction"],
                    _json_dump(item["skills"]),
                    _json_dump(item["highlights"]),
                    _json_dump(item["risks"]),
                    now,
                    now,
                )
                for item in seed["candidates"]
            ],
        )

    if _table_count(connection, "interviews") == 0:
        connection.executemany(
            """
            INSERT INTO interviews (
                id, candidate_name, role, round, mode, time_label, interviewer,
                status, decision_window, pack_status, summary, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    item["id"],
                    item["candidateName"],
                    item["role"],
                    item["round"],
                    item["mode"],
                    item["time"],
                    item["interviewer"],
                    item["status"],
                    item["decisionWindow"],
                    item["packStatus"],
                    item["summary"],
                    now,
                    now,
                )
                for item in seed["interviews"]
            ],
        )

    if _table_count(connection, "offers") == 0:
        connection.executemany(
            """
            INSERT INTO offers (
                id, candidate_id, job_id, candidate_name, opening_title, status,
                onboarding_owner, payroll_owner, payroll_handoff_status, salary_expectation,
                compensation_notes, handoff_summary, payroll_handoff_summary, next_action,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    item["id"],
                    item["candidateId"],
                    item["jobId"],
                    item["candidateName"],
                    item["openingTitle"],
                    item["status"],
                    item["onboardingOwner"],
                    item["payrollOwner"],
                    item["payrollHandoffStatus"],
                    item["salaryExpectation"],
                    item["compensationNotes"],
                    item["handoffSummary"],
                    item["payrollHandoffSummary"],
                    item["nextAction"],
                    now,
                    now,
                )
                for item in seed["offers"]
            ],
        )

    if _table_count(connection, "app_state") == 0:
        overview = seed["overview"]
        connection.executemany(
            "INSERT INTO app_state (key, value_json) VALUES (?, ?)",
            [
                ("overview_title", _json_dump(overview["title"])),
                ("overview_subtitle", _json_dump(overview["subtitle"])),
                ("overview_focus", _json_dump(overview["focus"])),
            ],
        )

    if _table_count(connection, "candidate_timeline_events") == 0:
        _seed_candidate_timeline_events(connection, seed)


def list_jobs(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT * FROM jobs
        ORDER BY
            CASE urgency WHEN 'critical' THEN 0 WHEN 'high' THEN 1 ELSE 2 END,
            updated_at DESC
        """
    ).fetchall()
    return [_job_from_row(row) for row in rows]


def list_candidates(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT * FROM candidates
        ORDER BY score DESC, created_at DESC
        """
    ).fetchall()
    return [_candidate_from_row(row) for row in rows]


def list_interviews(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT * FROM interviews
        ORDER BY time_label ASC, created_at DESC
        """
    ).fetchall()
    return [_interview_from_row(row) for row in rows]


def list_offers(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT * FROM offers
        ORDER BY updated_at DESC
        """
    ).fetchall()
    return [_offer_from_row(row) for row in rows]


def list_resume_intake_jobs(connection: sqlite3.Connection, limit: int = 12) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT * FROM resume_intake_jobs
        ORDER BY updated_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [_resume_intake_job_from_row(row) for row in rows]


def get_resume_intake_job(connection: sqlite3.Connection, intake_job_id: str) -> dict[str, Any]:
    row = connection.execute(
        "SELECT * FROM resume_intake_jobs WHERE id = ?",
        (intake_job_id,),
    ).fetchone()
    if not row:
        raise LookupError(f"Resume intake job not found: {intake_job_id}")

    items = connection.execute(
        """
        SELECT * FROM resume_intake_items
        WHERE intake_job_id = ?
        ORDER BY created_at ASC
        """,
        (intake_job_id,),
    ).fetchall()
    return _resume_intake_job_from_row(row, items=[_resume_intake_item_from_row(item) for item in items])


def list_candidate_timeline(connection: sqlite3.Connection, candidate_id: str) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT * FROM candidate_timeline_events
        WHERE candidate_id = ?
        ORDER BY rowid DESC, created_at DESC
        """,
        (candidate_id,),
    ).fetchall()
    return [_timeline_event_from_row(row) for row in rows]


def get_app_state(connection: sqlite3.Connection, key: str, fallback: Any) -> Any:
    row = connection.execute("SELECT value_json FROM app_state WHERE key = ?", (key,)).fetchone()
    if not row:
        return fallback
    return json.loads(row["value_json"])


def create_candidate(connection: sqlite3.Connection, payload: Mapping[str, Any]) -> dict[str, Any]:
    candidate_id = payload.get("id") or f"cand-{datetime.now().strftime('%Y%m%d%H%M%S%f')[-12:]}"
    now = _now_iso()
    record = {
        "id": candidate_id,
        "name": str(payload["name"]).strip(),
        "role": str(payload["role"]).strip(),
        "score": int(payload.get("score", 0) or 0),
        "status": str(payload.get("status") or "待经理复核").strip(),
        "city": str(payload.get("city") or "待确认").strip(),
        "experience": str(payload.get("experience") or "待确认").strip(),
        "owner": str(payload.get("owner") or "待分配").strip(),
        "source": str(payload.get("source") or "手动录入").strip(),
        "next_action": str(payload.get("next_action") or "运行 AI 初筛").strip(),
        "skills": [str(item).strip() for item in payload.get("skills", []) if str(item).strip()],
        "highlights": [str(item).strip() for item in payload.get("highlights", []) if str(item).strip()],
        "risks": [str(item).strip() for item in payload.get("risks", []) if str(item).strip()],
    }

    if not record["highlights"]:
        if record["skills"]:
            record["highlights"] = [f"已录入技能：{'、'.join(record['skills'][:4])}，待补项目证据。"]
        else:
            record["highlights"] = ["候选人已录入，待补简历内容并运行 AI 初筛。"]

    if not record["risks"]:
        record["risks"] = ["尚未完成 AI 风险识别，建议补齐简历后继续。"]

    connection.execute(
        """
        INSERT INTO candidates (
            id, name, role, score, status, city, experience, owner, source,
            next_action, skills_json, highlights_json, risks_json, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record["id"],
            record["name"],
            record["role"],
            record["score"],
            record["status"],
            record["city"],
            record["experience"],
            record["owner"],
            record["source"],
            record["next_action"],
            _json_dump(record["skills"]),
            _json_dump(record["highlights"]),
            _json_dump(record["risks"]),
            now,
            now,
        ),
    )
    _append_candidate_timeline_event(
        connection,
        candidate_id=record["id"],
        event_type="candidate_created",
        title="候选人已录入",
        detail=f"来自{record['source']}，目标岗位：{record['role']}，当前状态：{record['status']}。",
        actor=record["owner"],
        created_at=now,
    )
    connection.commit()
    return record


def create_job(connection: sqlite3.Connection, payload: Mapping[str, Any]) -> dict[str, Any]:
    job_id = payload.get("id") or f"job-{datetime.now().strftime('%Y%m%d%H%M%S%f')[-12:]}"
    now = _now_iso()
    record = {
        "id": job_id,
        "title": str(payload["title"]).strip(),
        "team": str(payload.get("team") or "待定团队").strip(),
        "location": str(payload.get("location") or "待定").strip(),
        "mode": str(payload.get("mode") or "Hybrid").strip(),
        "headcount": int(payload.get("headcount", 1) or 1),
        "stage": str(payload.get("stage") or "开放招聘").strip(),
        "updated_at_label": str(payload.get("updated_at_label") or _updated_label()).strip(),
        "applicants": int(payload.get("applicants", 0) or 0),
        "screened": int(payload.get("screened", 0) or 0),
        "interviews": int(payload.get("interviews", 0) or 0),
        "offers": int(payload.get("offers", 0) or 0),
        "owner": str(payload.get("owner") or "待分配").strip(),
        "urgency": str(payload.get("urgency") or "medium").strip(),
        "summary": str(payload.get("summary") or "待补岗位说明。").strip(),
        "skills": [str(item).strip() for item in payload.get("skills", []) if str(item).strip()],
    }

    connection.execute(
        """
        INSERT INTO jobs (
            id, title, team, location, mode, headcount, stage, updated_at_label,
            applicants, screened, interviews, offers, owner, urgency, summary,
            skills_json, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record["id"],
            record["title"],
            record["team"],
            record["location"],
            record["mode"],
            record["headcount"],
            record["stage"],
            record["updated_at_label"],
            record["applicants"],
            record["screened"],
            record["interviews"],
            record["offers"],
            record["owner"],
            record["urgency"],
            record["summary"],
            _json_dump(record["skills"]),
            now,
            now,
        ),
    )
    connection.commit()
    return {
        "id": record["id"],
        "title": record["title"],
        "team": record["team"],
        "location": record["location"],
        "mode": record["mode"],
        "headcount": record["headcount"],
        "stage": record["stage"],
        "updatedAt": record["updated_at_label"],
        "applicants": record["applicants"],
        "screened": record["screened"],
        "interviews": record["interviews"],
        "offers": record["offers"],
        "owner": record["owner"],
        "urgency": record["urgency"],
        "summary": record["summary"],
        "skills": record["skills"],
    }


def create_interview(connection: sqlite3.Connection, payload: Mapping[str, Any]) -> dict[str, Any]:
    interview_id = payload.get("id") or f"int-{datetime.now().strftime('%Y%m%d%H%M%S%f')[-12:]}"
    now = _now_iso()
    record = {
        "id": interview_id,
        "candidate_name": str(payload["candidate_name"]).strip(),
        "role": str(payload["role"]).strip(),
        "round": str(payload.get("round") or "技术一面").strip(),
        "mode": str(payload.get("mode") or "视频").strip(),
        "time_label": str(payload.get("time_label") or _updated_label()).strip(),
        "interviewer": str(payload.get("interviewer") or "待分配").strip(),
        "status": str(payload.get("status") or "已安排").strip(),
        "decision_window": str(payload.get("decision_window") or "面试后 24 小时").strip(),
        "pack_status": str(payload.get("pack_status") or "待补充").strip(),
        "summary": str(payload.get("summary") or "待补面试目标与问题清单。").strip(),
    }

    connection.execute(
        """
        INSERT INTO interviews (
            id, candidate_name, role, round, mode, time_label, interviewer,
            status, decision_window, pack_status, summary, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record["id"],
            record["candidate_name"],
            record["role"],
            record["round"],
            record["mode"],
            record["time_label"],
            record["interviewer"],
            record["status"],
            record["decision_window"],
            record["pack_status"],
            record["summary"],
            now,
            now,
        ),
    )

    connection.execute(
        """
        UPDATE jobs
        SET interviews = interviews + 1,
            updated_at = ?,
            updated_at_label = ?
        WHERE title = ?
        """,
        (
            now,
            _updated_label(),
            record["role"],
        ),
    )
    candidate_row = _find_candidate_row_by_name_role(connection, record["candidate_name"], record["role"])
    if candidate_row:
        next_action = f"等待{record['round']}反馈"
        connection.execute(
            """
            UPDATE candidates
            SET status = ?, next_action = ?, updated_at = ?
            WHERE id = ?
            """,
            ("面试中", next_action, now, candidate_row["id"]),
        )
        _append_candidate_timeline_event(
            connection,
            candidate_id=candidate_row["id"],
            event_type="interview_scheduled",
            title=f"已安排{record['round']}",
            detail=f"{record['time_label']} · {record['interviewer']} · {record['mode']}。",
            actor=record["interviewer"],
            created_at=now,
        )
    connection.commit()
    return _interview_payload(record)


def apply_interview_feedback(connection: sqlite3.Connection, interview_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    interview_row = connection.execute("SELECT * FROM interviews WHERE id = ?", (interview_id,)).fetchone()
    if not interview_row:
        raise LookupError(f"Interview not found: {interview_id}")

    now = _now_iso()
    decision = str(payload.get("decision") or "待补面").strip()
    summary = str(payload.get("summary") or "待补反馈摘要。").strip()
    strengths = [str(item).strip() for item in payload.get("strengths", []) if str(item).strip()]
    concerns = [str(item).strip() for item in payload.get("concerns", []) if str(item).strip()]
    next_step = str(payload.get("next_step") or _default_next_step(decision)).strip()
    actor = str(payload.get("actor") or interview_row["interviewer"] or "面试官").strip()
    interview_status = _interview_status_from_decision(decision)

    existing_feedback = connection.execute(
        "SELECT id FROM interview_feedbacks WHERE interview_id = ?",
        (interview_id,),
    ).fetchone()
    feedback_id = existing_feedback["id"] if existing_feedback else f"fb-{datetime.now().strftime('%Y%m%d%H%M%S%f')[-12:]}"

    if existing_feedback:
        connection.execute(
            """
            UPDATE interview_feedbacks
            SET decision = ?, summary = ?, strengths_json = ?, concerns_json = ?, next_step = ?, actor = ?, updated_at = ?
            WHERE interview_id = ?
            """,
            (
                decision,
                summary,
                _json_dump(strengths),
                _json_dump(concerns),
                next_step,
                actor,
                now,
                interview_id,
            ),
        )
    else:
        connection.execute(
            """
            INSERT INTO interview_feedbacks (
                id, interview_id, decision, summary, strengths_json, concerns_json,
                next_step, actor, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                feedback_id,
                interview_id,
                decision,
                summary,
                _json_dump(strengths),
                _json_dump(concerns),
                next_step,
                actor,
                now,
                now,
            ),
        )

    connection.execute(
        """
        UPDATE interviews
        SET status = ?, summary = ?, updated_at = ?
        WHERE id = ?
        """,
        (interview_status, summary, now, interview_id),
    )

    candidate_row = _find_candidate_row_by_name_role(connection, interview_row["candidate_name"], interview_row["role"])
    candidate_payload = None
    timeline_payload: list[dict[str, Any]] = []
    if candidate_row:
        candidate_status = _candidate_status_from_decision(decision)
        connection.execute(
            """
            UPDATE candidates
            SET status = ?, next_action = ?, updated_at = ?
            WHERE id = ?
            """,
            (candidate_status, next_step, now, candidate_row["id"]),
        )
        _append_candidate_timeline_event(
            connection,
            candidate_id=candidate_row["id"],
            event_type="interview_feedback",
            title=f"{interview_row['round']}反馈：{decision}",
            detail=_build_feedback_timeline_detail(summary, strengths, concerns, next_step),
            actor=actor,
            created_at=now,
        )
        candidate_payload = _candidate_from_row(
            connection.execute("SELECT * FROM candidates WHERE id = ?", (candidate_row["id"],)).fetchone()
        )
        timeline_payload = list_candidate_timeline(connection, candidate_row["id"])

    connection.commit()
    updated_interview = _interview_from_row(connection.execute("SELECT * FROM interviews WHERE id = ?", (interview_id,)).fetchone())
    return {
        "feedback": {
            "id": feedback_id,
            "decision": decision,
            "summary": summary,
            "strengths": strengths,
            "concerns": concerns,
            "nextStep": next_step,
            "actor": actor,
        },
        "interview": updated_interview,
        "candidate": candidate_payload,
        "timeline": timeline_payload,
    }


def create_offer(connection: sqlite3.Connection, payload: Mapping[str, Any]) -> dict[str, Any]:
    candidate_id = str(payload["candidate_id"]).strip()
    job_id = str(payload["job_id"]).strip()
    candidate_row = connection.execute("SELECT * FROM candidates WHERE id = ?", (candidate_id,)).fetchone()
    if not candidate_row:
        raise LookupError(f"Candidate not found: {candidate_id}")
    job_row = connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not job_row:
        raise LookupError(f"Job not found: {job_id}")

    now = _now_iso()
    offer_id = payload.get("id") or f"offer-{datetime.now().strftime('%Y%m%d%H%M%S%f')[-12:]}"
    status = str(payload.get("status") or "Accepted").strip()
    onboarding_owner = str(payload.get("onboarding_owner") or candidate_row["owner"] or job_row["owner"] or "待分配").strip()
    payroll_owner = str(payload.get("payroll_owner") or onboarding_owner).strip()
    payroll_handoff_status = str(payload.get("payroll_handoff_status") or "Not Started").strip()
    salary_expectation = str(payload.get("salary_expectation") or "待补充").strip()
    compensation_notes = str(payload.get("compensation_notes") or "待确认薪资构成、试用期和补贴项。").strip()
    next_action = get_offer_next_action(status, payroll_handoff_status)
    handoff_summary = build_offer_handoff_notes(
        candidate_name=candidate_row["name"],
        opening_title=job_row["title"],
        offer_status=status,
        onboarding_owner=onboarding_owner,
        payroll_handoff_status=payroll_handoff_status,
        salary_expectation=salary_expectation,
        compensation_notes=compensation_notes,
    )
    payroll_handoff_summary = build_payroll_handoff_summary(
        candidate_name=candidate_row["name"],
        opening_title=job_row["title"],
        payroll_owner=payroll_owner,
        payroll_handoff_status=payroll_handoff_status,
        salary_expectation=salary_expectation,
        opening_salary_range="",
        compensation_notes=compensation_notes,
    )

    connection.execute(
        """
        INSERT INTO offers (
            id, candidate_id, job_id, candidate_name, opening_title, status,
            onboarding_owner, payroll_owner, payroll_handoff_status, salary_expectation,
            compensation_notes, handoff_summary, payroll_handoff_summary, next_action,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            offer_id,
            candidate_id,
            job_id,
            candidate_row["name"],
            job_row["title"],
            status,
            onboarding_owner,
            payroll_owner,
            payroll_handoff_status,
            salary_expectation,
            compensation_notes,
            handoff_summary,
            payroll_handoff_summary,
            next_action,
            now,
            now,
        ),
    )
    connection.execute(
        """
        UPDATE jobs
        SET offers = offers + 1,
            updated_at = ?,
            updated_at_label = ?
        WHERE id = ?
        """,
        (now, _updated_label(), job_id),
    )
    connection.execute(
        """
        UPDATE candidates
        SET status = ?, next_action = ?, updated_at = ?
        WHERE id = ?
        """,
        (_candidate_status_from_offer_status(status), next_action, now, candidate_id),
    )
    _append_candidate_timeline_event(
        connection,
        candidate_id=candidate_id,
        event_type="offer_created",
        title="Offer 交接已创建",
        detail=f"状态：{status}。薪资期望：{salary_expectation}。下一步：{next_action}",
        actor=onboarding_owner,
        created_at=now,
    )
    connection.commit()
    return _offer_from_row(connection.execute("SELECT * FROM offers WHERE id = ?", (offer_id,)).fetchone())


def mark_offer_payroll_ready(connection: sqlite3.Connection, offer_id: str) -> dict[str, Any]:
    offer_row = connection.execute("SELECT * FROM offers WHERE id = ?", (offer_id,)).fetchone()
    if not offer_row:
        raise LookupError(f"Offer not found: {offer_id}")

    now = _now_iso()
    payroll_handoff_status = "Ready"
    next_action = get_offer_next_action(offer_row["status"], payroll_handoff_status)
    payroll_handoff_summary = build_payroll_handoff_summary(
        candidate_name=offer_row["candidate_name"],
        opening_title=offer_row["opening_title"],
        payroll_owner=offer_row["payroll_owner"],
        payroll_handoff_status=payroll_handoff_status,
        salary_expectation=offer_row["salary_expectation"],
        opening_salary_range="",
        compensation_notes=offer_row["compensation_notes"],
    )
    handoff_summary = build_offer_handoff_notes(
        candidate_name=offer_row["candidate_name"],
        opening_title=offer_row["opening_title"],
        offer_status=offer_row["status"],
        onboarding_owner=offer_row["onboarding_owner"],
        payroll_handoff_status=payroll_handoff_status,
        salary_expectation=offer_row["salary_expectation"],
        compensation_notes=offer_row["compensation_notes"],
    )

    connection.execute(
        """
        UPDATE offers
        SET payroll_handoff_status = ?,
            next_action = ?,
            handoff_summary = ?,
            payroll_handoff_summary = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            payroll_handoff_status,
            next_action,
            handoff_summary,
            payroll_handoff_summary,
            now,
            offer_id,
        ),
    )
    connection.execute(
        """
        UPDATE candidates
        SET next_action = ?, updated_at = ?
        WHERE id = ?
        """,
        (next_action, now, offer_row["candidate_id"]),
    )
    _append_candidate_timeline_event(
        connection,
        candidate_id=offer_row["candidate_id"],
        event_type="offer_payroll_ready",
        title="薪酬交接已就绪",
        detail=f"薪酬负责人：{offer_row['payroll_owner']}。下一步：{next_action}",
        actor=offer_row["payroll_owner"],
        created_at=now,
    )
    connection.commit()
    updated_offer = _offer_from_row(connection.execute("SELECT * FROM offers WHERE id = ?", (offer_id,)).fetchone())
    updated_candidate = _candidate_from_row(connection.execute("SELECT * FROM candidates WHERE id = ?", (offer_row["candidate_id"],)).fetchone())
    return {
        "offer": updated_offer,
        "candidate": updated_candidate,
        "timeline": list_candidate_timeline(connection, offer_row["candidate_id"]),
    }


def create_resume_intake_job(
    connection: sqlite3.Connection,
    payload: Mapping[str, Any],
    archive_bytes: bytes,
) -> dict[str, Any]:
    job_row = connection.execute("SELECT * FROM jobs WHERE id = ?", (str(payload["job_id"]).strip(),)).fetchone()
    if not job_row:
        raise LookupError(f"Job not found: {payload['job_id']}")

    intake_job_id = payload.get("id") or f"intake-{datetime.now().strftime('%Y%m%d%H%M%S%f')[-12:]}"
    archive_name = str(payload.get("archive_name") or "resume_bundle.zip").strip() or "resume_bundle.zip"
    now = _now_iso()
    archive_dir = DEFAULT_INTAKE_ARCHIVE_DIR / intake_job_id
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_path = archive_dir / archive_name
    archive_path.write_bytes(archive_bytes)

    connection.execute(
        """
        INSERT INTO resume_intake_jobs (
            id, archive_name, archive_path, job_id, job_title, owner, source_label, status,
            total_files, parsed_count, unsupported_count, failed_count, created_candidate_count,
            error_message, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            intake_job_id,
            archive_name,
            str(archive_path),
            job_row["id"],
            job_row["title"],
            str(payload.get("owner") or job_row["owner"] or "待分配").strip(),
            str(payload.get("source") or "ZIP 简历包").strip(),
            "Queued",
            0,
            0,
            0,
            0,
            0,
            "",
            now,
            now,
        ),
    )
    connection.commit()
    return _resume_intake_job_from_row(connection.execute("SELECT * FROM resume_intake_jobs WHERE id = ?", (intake_job_id,)).fetchone())


def run_resume_intake_job(intake_job_id: str) -> None:
    try:
        with db_session() as connection:
            job_row = connection.execute("SELECT * FROM resume_intake_jobs WHERE id = ?", (intake_job_id,)).fetchone()
            if not job_row:
                raise LookupError(f"Resume intake job not found: {intake_job_id}")

            _update_resume_intake_job_status(connection, intake_job_id, "Running")
            archive_path = Path(job_row["archive_path"])
            job_target = connection.execute("SELECT * FROM jobs WHERE id = ?", (job_row["job_id"],)).fetchone()
            if not job_target:
                raise LookupError(f"Job not found for intake job: {job_row['job_id']}")

            extracted_items = extract_resume_archive(archive_path, skill_lexicon=_json_load(job_target["skills_json"]))
            counters = {
                "total_files": len(extracted_items),
                "parsed_count": 0,
                "unsupported_count": 0,
                "failed_count": 0,
                "created_candidate_count": 0,
            }

            for index, item in enumerate(extracted_items, start=1):
                item_status = str(item.get("status") or "Failed")
                reason = str(item.get("reason") or "")
                candidate_id = ""
                parsed_resume = item.get("parsed_resume") or {}
                parser_engine = str(item.get("parser_engine") or "")

                if item_status == "Parsed":
                    counters["parsed_count"] += 1
                    try:
                        created_candidate = _create_candidate_from_resume_item(
                            connection,
                            parsed_item=item,
                            intake_job_row=job_row,
                            job_row=job_target,
                        )
                        candidate_id = created_candidate["id"]
                        counters["created_candidate_count"] += 1
                    except Exception as exc:
                        item_status = "Failed"
                        reason = f"候选人写入失败：{exc}"
                        counters["failed_count"] += 1
                elif item_status == "Unsupported":
                    counters["unsupported_count"] += 1
                else:
                    counters["failed_count"] += 1

                connection.execute(
                    """
                    INSERT INTO resume_intake_items (
                        id, intake_job_id, file_name, file_extension, status, reason,
                        parser_engine, parsed_resume_json, candidate_id, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"intake-item-{intake_job_id}-{index}",
                        intake_job_id,
                        str(item.get("file_name") or ""),
                        str(item.get("file_extension") or ""),
                        item_status,
                        reason,
                        parser_engine,
                        _json_dump(parsed_resume),
                        candidate_id,
                        _now_iso(),
                    ),
                )

            if counters["created_candidate_count"]:
                connection.execute(
                    """
                    UPDATE jobs
                    SET applicants = applicants + ?,
                        screened = screened + ?,
                        updated_at = ?,
                        updated_at_label = ?
                    WHERE id = ?
                    """,
                    (
                        counters["created_candidate_count"],
                        counters["created_candidate_count"],
                        _now_iso(),
                        _updated_label(),
                        job_target["id"],
                    ),
                )

            connection.execute(
                """
                UPDATE resume_intake_jobs
                SET status = ?,
                    total_files = ?,
                    parsed_count = ?,
                    unsupported_count = ?,
                    failed_count = ?,
                    created_candidate_count = ?,
                    error_message = '',
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    "Completed",
                    counters["total_files"],
                    counters["parsed_count"],
                    counters["unsupported_count"],
                    counters["failed_count"],
                    counters["created_candidate_count"],
                    _now_iso(),
                    intake_job_id,
                ),
            )
            connection.commit()
    except Exception as exc:
        with db_session() as connection:
            connection.execute(
                """
                UPDATE resume_intake_jobs
                SET status = ?, error_message = ?, updated_at = ?
                WHERE id = ?
                """,
                ("Failed", str(exc), _now_iso(), intake_job_id),
            )
            connection.commit()


def _job_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "team": row["team"],
        "location": row["location"],
        "mode": row["mode"],
        "headcount": row["headcount"],
        "stage": row["stage"],
        "updatedAt": row["updated_at_label"],
        "applicants": row["applicants"],
        "screened": row["screened"],
        "interviews": row["interviews"],
        "offers": row["offers"],
        "owner": row["owner"],
        "urgency": row["urgency"],
        "summary": row["summary"],
        "skills": _json_load(row["skills_json"]),
    }


def _candidate_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "role": row["role"],
        "score": row["score"],
        "status": row["status"],
        "city": row["city"],
        "experience": row["experience"],
        "owner": row["owner"],
        "source": row["source"],
        "nextAction": row["next_action"],
        "skills": _json_load(row["skills_json"]),
        "highlights": _json_load(row["highlights_json"]),
        "risks": _json_load(row["risks_json"]),
    }


def _interview_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return _interview_payload(
        {
            "id": row["id"],
            "candidate_name": row["candidate_name"],
            "role": row["role"],
            "round": row["round"],
            "mode": row["mode"],
            "time_label": row["time_label"],
            "interviewer": row["interviewer"],
            "status": row["status"],
            "decision_window": row["decision_window"],
            "pack_status": row["pack_status"],
            "summary": row["summary"],
        }
    )


def _interview_payload(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": record["id"],
        "candidateName": record["candidate_name"],
        "role": record["role"],
        "round": record["round"],
        "mode": record["mode"],
        "time": record["time_label"],
        "interviewer": record["interviewer"],
        "status": record["status"],
        "decisionWindow": record["decision_window"],
        "packStatus": record["pack_status"],
        "summary": record["summary"],
    }


def _offer_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "candidateId": row["candidate_id"],
        "jobId": row["job_id"],
        "candidateName": row["candidate_name"],
        "openingTitle": row["opening_title"],
        "status": row["status"],
        "onboardingOwner": row["onboarding_owner"],
        "payrollOwner": row["payroll_owner"],
        "payrollHandoffStatus": row["payroll_handoff_status"],
        "salaryExpectation": row["salary_expectation"],
        "compensationNotes": row["compensation_notes"],
        "handoffSummary": row["handoff_summary"],
        "payrollHandoffSummary": row["payroll_handoff_summary"],
        "nextAction": row["next_action"],
    }


def _resume_intake_job_from_row(row: sqlite3.Row, *, items: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "id": row["id"],
        "archiveName": row["archive_name"],
        "jobId": row["job_id"],
        "jobTitle": row["job_title"],
        "owner": row["owner"],
        "source": row["source_label"],
        "status": row["status"],
        "summary": {
            "totalFiles": row["total_files"],
            "parsedCount": row["parsed_count"],
            "unsupportedCount": row["unsupported_count"],
            "failedCount": row["failed_count"],
            "createdCandidateCount": row["created_candidate_count"],
        },
        "errorMessage": row["error_message"],
        "updatedAt": row["updated_at"],
        "items": items or [],
    }


def _resume_intake_item_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "fileName": row["file_name"],
        "fileExtension": row["file_extension"],
        "status": row["status"],
        "reason": row["reason"],
        "parserEngine": row["parser_engine"],
        "parsedResume": _json_load(row["parsed_resume_json"]),
        "candidateId": row["candidate_id"],
    }


def _timeline_event_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "eventType": row["event_type"],
        "title": row["title"],
        "detail": row["detail"],
        "actor": row["actor"],
        "happenedAt": row["happened_at_label"],
    }


def _seed_candidate_timeline_events(connection: sqlite3.Connection, seed: Mapping[str, Any]) -> None:
    candidate_map = {(item["name"], item["role"]): item["id"] for item in seed["candidates"]}
    rows: list[tuple[str, str, str, str, str, str, str]] = []

    for index, item in enumerate(seed["candidates"], start=1):
        rows.append(
            (
                f"seed-candidate-{index}",
                item["id"],
                "candidate_seeded",
                "候选人已入池",
                f"来自{item['source']}，当前状态：{item['status']}，下一步：{item['nextAction']}。",
                item["owner"],
                "初始导入",
            )
        )

    for index, item in enumerate(seed["interviews"], start=1):
        candidate_id = candidate_map.get((item["candidateName"], item["role"]))
        if not candidate_id:
            continue
        rows.append(
            (
                f"seed-interview-{index}",
                candidate_id,
                "interview_seeded",
                f"已安排{item['round']}",
                f"{item['time']} · {item['interviewer']} · {item['mode']}。",
                item["interviewer"],
                item["time"],
            )
        )

    for index, item in enumerate(seed["offers"], start=1):
        rows.append(
            (
                f"seed-offer-{index}",
                item["candidateId"],
                "offer_seeded",
                "Offer 交接已创建",
                f"状态：{item['status']}。下一步：{item['nextAction']}",
                item["onboardingOwner"],
                "Offer 在途",
            )
        )

    connection.executemany(
        """
        INSERT INTO candidate_timeline_events (
            id, candidate_id, event_type, title, detail, actor, happened_at_label, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                event_id,
                candidate_id,
                event_type,
                title,
                detail,
                actor,
                happened_at_label,
                _now_iso(),
            )
            for event_id, candidate_id, event_type, title, detail, actor, happened_at_label in rows
        ],
    )


def _append_candidate_timeline_event(
    connection: sqlite3.Connection,
    *,
    candidate_id: str,
    event_type: str,
    title: str,
    detail: str,
    actor: str,
    created_at: str | None = None,
) -> None:
    timestamp = created_at or _now_iso()
    connection.execute(
        """
        INSERT INTO candidate_timeline_events (
            id, candidate_id, event_type, title, detail, actor, happened_at_label, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            f"evt-{datetime.now().strftime('%Y%m%d%H%M%S%f')[-12:]}",
            candidate_id,
            event_type,
            title,
            detail,
            actor or "系统",
            _updated_label(),
            timestamp,
        ),
    )


def _update_resume_intake_job_status(connection: sqlite3.Connection, intake_job_id: str, status: str) -> None:
    connection.execute(
        """
        UPDATE resume_intake_jobs
        SET status = ?, updated_at = ?
        WHERE id = ?
        """,
        (status, _now_iso(), intake_job_id),
    )
    connection.commit()


def _find_candidate_row_by_name_role(connection: sqlite3.Connection, name: str, role: str) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT * FROM candidates
        WHERE name = ? AND role = ?
        ORDER BY updated_at DESC
        LIMIT 1
        """,
        (name, role),
    ).fetchone()


def _create_candidate_from_resume_item(
    connection: sqlite3.Connection,
    *,
    parsed_item: Mapping[str, Any],
    intake_job_row: sqlite3.Row,
    job_row: sqlite3.Row,
) -> dict[str, Any]:
    parsed_resume = parsed_item.get("parsed_resume") or {}
    screening = screen_candidate(
        parsed_resume=parsed_resume,
        job_requirements=_build_job_requirements(job_row),
        preferred_skills=" ".join(_json_load(job_row["skills_json"])),
        preferred_city=job_row["location"],
    )
    recommended_status = str(screening.get("recommended_status") or "Ready for Review")
    name = str(parsed_resume.get("name") or Path(str(parsed_item.get("file_name") or "候选人")).stem).strip()
    years = float(parsed_resume.get("years_of_experience", 0) or 0)
    experience = f"{years:g} 年" if years else "待确认"
    candidate = create_candidate(
        connection,
        {
            "name": name,
            "role": job_row["title"],
            "city": str(parsed_resume.get("city") or "待确认").strip(),
            "experience": experience,
            "owner": intake_job_row["owner"],
            "source": intake_job_row["source_label"],
            "status": _candidate_status_from_screening_status(recommended_status),
            "next_action": get_screening_next_action(recommended_status),
            "score": int(screening.get("overall_score", 0) or 0),
            "skills": parsed_resume.get("skills") or [],
            "highlights": screening.get("strengths") or [],
            "risks": screening.get("risks") or [],
        },
    )
    _append_candidate_timeline_event(
        connection,
        candidate_id=candidate["id"],
        event_type="resume_intake_completed",
        title="ZIP 简历导入完成",
        detail=f"文件：{parsed_item.get('file_name') or '未知文件'}。自动初筛分数：{screening.get('overall_score', 0)}/100。",
        actor=intake_job_row["owner"],
        created_at=_now_iso(),
    )
    return candidate


def _build_feedback_timeline_detail(summary: str, strengths: list[str], concerns: list[str], next_step: str) -> str:
    parts = [summary]
    if strengths:
        parts.append(f"亮点：{'；'.join(strengths[:2])}")
    if concerns:
        parts.append(f"风险：{'；'.join(concerns[:2])}")
    parts.append(f"下一步：{next_step}")
    return " ".join(part for part in parts if part)


def _interview_status_from_decision(decision: str) -> str:
    return {
        "通过": "已通过",
        "淘汰": "已淘汰",
        "待补面": "待补面",
    }.get(decision, "待反馈")


def _candidate_status_from_decision(decision: str) -> str:
    return {
        "通过": "建议推进",
        "淘汰": "暂不推进",
        "待补面": "待补充信息",
    }.get(decision, "待经理复核")


def _default_next_step(decision: str) -> str:
    return {
        "通过": "安排下一轮面试",
        "淘汰": "同步淘汰结论",
        "待补面": "补充信息后再决策",
    }.get(decision, "等待反馈同步")


def _candidate_status_from_offer_status(status: str) -> str:
    return {
        "Accepted": "Offer 已接受",
        "Rejected": "Offer 未接受",
    }.get(status, "Offer 推进中")


def _candidate_status_from_screening_status(status: str) -> str:
    return {
        "Advance": "建议推进",
        "Ready for Review": "待经理复核",
        "Hold": "建议暂缓",
    }.get(status, "待经理复核")


def _build_job_requirements(job_row: sqlite3.Row) -> str:
    skills = _json_load(job_row["skills_json"])
    return " ".join(
        part
        for part in [
            str(job_row["title"] or ""),
            str(job_row["summary"] or ""),
            " ".join(skills),
        ]
        if part
    )


def _table_count(connection: sqlite3.Connection, table_name: str) -> int:
    row = connection.execute(f"SELECT COUNT(*) AS count FROM {table_name}").fetchone()
    return int(row["count"])


def _json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _json_load(value: str) -> Any:
    return json.loads(value) if value else []


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _updated_label() -> str:
    return datetime.now().strftime("%m-%d %H:%M")
