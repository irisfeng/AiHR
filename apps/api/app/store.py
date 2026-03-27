from __future__ import annotations

import json
import os
import sqlite3
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

DEMO_DATA_FILE = Path(__file__).resolve().parents[2] / "shared" / "demo-data.json"
DEFAULT_DATABASE_PATH = Path(__file__).resolve().parents[1] / "data" / "aihr.sqlite3"
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
