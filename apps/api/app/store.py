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
DATABASE_PATH = Path(os.getenv("AIHR_API_DATABASE_PATH") or DEFAULT_DATABASE_PATH)


def load_demo_seed() -> dict[str, Any]:
    return json.loads(DEMO_DATA_FILE.read_text(encoding="utf-8"))


def get_database_path() -> Path:
    return DATABASE_PATH


def connect_db() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
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
    return {
        "id": row["id"],
        "candidateName": row["candidate_name"],
        "role": row["role"],
        "round": row["round"],
        "mode": row["mode"],
        "time": row["time_label"],
        "interviewer": row["interviewer"],
        "status": row["status"],
        "decisionWindow": row["decision_window"],
        "packStatus": row["pack_status"],
        "summary": row["summary"],
    }


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
