from __future__ import annotations

from typing import Any
from urllib.parse import unquote

from aihr.setup.workspace import (
    INTERVIEWER_WORKSPACE_LABEL,
    MANAGER_WORKSPACE_LABEL,
    WORKSPACE_BLOCK_LABEL,
)

AIHR_DESK_HOME = "/app/aihr-hiring-hq"
LEGACY_WORKSPACE_LABELS = {
    "AIHR 招聘作战台": WORKSPACE_BLOCK_LABEL,
    "AIHR 用人经理台": MANAGER_WORKSPACE_LABEL,
    "AIHR 面试官台": INTERVIEWER_WORKSPACE_LABEL,
}

WORKSPACE_PATH_REDIRECTS = {
    "/app/aihr-招聘总览": AIHR_DESK_HOME,
    "/app/aihr-用人经理中心": "/app/aihr-manager-review",
    "/app/aihr-面试协同中心": "/app/aihr-interview-desk",
}

LEGACY_ROUTE_HISTORY_MAP = {
    f"Workspaces/{source}": f"Workspaces/{target}"
    for source, target in LEGACY_WORKSPACE_LABELS.items()
}

BLOCKED_ROUTE_HISTORY = {"Workspaces/HR"}


def normalize_workspace_label(label: str | None) -> str | None:
    normalized = (label or "").strip()
    if not normalized:
        return None
    return LEGACY_WORKSPACE_LABELS.get(normalized, normalized)


def normalize_route_history_route(route: str | None) -> str | None:
    normalized = (route or "").strip()
    if not normalized:
        return None
    return LEGACY_ROUTE_HISTORY_MAP.get(normalized, normalized)


def normalize_desk_path(path: str | None) -> str | None:
    normalized = unquote((path or "").strip())
    if not normalized:
        return None
    if normalized == "/app":
        return AIHR_DESK_HOME
    return WORKSPACE_PATH_REDIRECTS.get(normalized, normalized)


def should_hide_route_history(route: str | None) -> bool:
    normalized = normalize_route_history_route(route)
    return not normalized or normalized in BLOCKED_ROUTE_HISTORY


def should_hide_frequent_link(route: str | None) -> bool:
    normalized = normalize_route_history_route(route)
    return should_hide_route_history(normalized) or str(normalized).startswith("Workspaces/")


def sanitize_frequently_visited_links(links: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    sanitized: list[dict[str, Any]] = []
    seen: set[str] = set()

    for link in links or []:
        route = normalize_route_history_route(link.get("route"))
        if should_hide_frequent_link(route) or route in seen:
            continue

        sanitized.append({**link, "route": route})
        seen.add(route)

    return sanitized


def cleanup_route_history(user: str | None = None) -> None:
    import frappe

    if not frappe.db.exists("DocType", "Route History"):
        return

    for source, target in LEGACY_ROUTE_HISTORY_MAP.items():
        if user:
            frappe.db.sql(
                """
                update `tabRoute History`
                set route=%s
                where route=%s and user=%s
                """,
                (target, source, user),
            )
        else:
            frappe.db.sql(
                """
                update `tabRoute History`
                set route=%s
                where route=%s
                """,
                (target, source),
            )

    delete_filters: dict[str, str] = {"route": "Workspaces/HR"}
    if user:
        delete_filters["user"] = user
    frappe.db.delete("Route History", delete_filters)


def extend_bootinfo(bootinfo) -> None:
    import frappe

    user = getattr(frappe.session, "user", None)
    if not user or user == "Guest":
        return

    cleanup_route_history(user)
    bootinfo.frequently_visited_links = sanitize_frequently_visited_links(
        list(bootinfo.get("frequently_visited_links") or [])
    )


def redirect_desk_root() -> None:
    import frappe
    from werkzeug.routing import RequestRedirect

    request = getattr(frappe.local, "request", None)
    if not request or request.method not in {"GET", "HEAD"}:
        return

    target = normalize_desk_path(getattr(request, "path", ""))
    if target and target != request.path:
        raise RequestRedirect(target)
