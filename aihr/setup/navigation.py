from __future__ import annotations

from typing import Any
from urllib.parse import unquote

from aihr.setup.access import WORKSPACE_ROLE_BINDINGS, preferred_workspace_for_roles
from aihr.setup.workspace import (
    INTERVIEWER_WORKSPACE_LABEL,
    INTERVIEWER_WORKSPACE_NAME,
    MANAGER_WORKSPACE_LABEL,
    MANAGER_WORKSPACE_NAME,
    WORKSPACE_NAME,
    WORKSPACE_BLOCK_LABEL,
)

WORKSPACE_ROUTES = {
    WORKSPACE_NAME: "/app/aihr-hiring-hq",
    MANAGER_WORKSPACE_NAME: "/app/aihr-manager-review",
    INTERVIEWER_WORKSPACE_NAME: "/app/aihr-interview-desk",
}

ROUTE_TO_WORKSPACE = {route: workspace for workspace, route in WORKSPACE_ROUTES.items()}
AIHR_DESK_HOME = WORKSPACE_ROUTES[WORKSPACE_NAME]
PORTAL_PATH_REDIRECTS = {
    "/me": AIHR_DESK_HOME,
    "/my-account": AIHR_DESK_HOME,
}
DESK_PREFIX_REDIRECTS = (
    "/app/user-profile",
    "/app/leaderboard",
)
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


def normalize_desk_path(
    path: str | None,
    user: str | None = None,
    role_names: list[str] | tuple[str, ...] | set[str] | None = None,
) -> str | None:
    normalized = unquote((path or "").strip())
    preferred_home = get_preferred_desk_home(user, role_names)
    if not normalized:
        return None
    if normalized == "/" and user and user != "Guest":
        return preferred_home
    if normalized == "/app":
        return preferred_home
    if normalized in PORTAL_PATH_REDIRECTS:
        return preferred_home
    if any(normalized.startswith(prefix) for prefix in DESK_PREFIX_REDIRECTS):
        return preferred_home

    redirected = WORKSPACE_PATH_REDIRECTS.get(normalized, normalized)
    if user and user != "Guest" and not user_can_access_workspace_path(user, redirected, role_names):
        return preferred_home
    return redirected


def is_probably_logged_in_system_user(user: str | None, cookies: dict[str, Any] | None = None) -> bool:
    if user and user != "Guest":
        return True

    cookie_values = cookies or {}
    return cookie_values.get("system_user") == "yes" and cookie_values.get("user_id") not in {
        None,
        "",
        "Guest",
    }


def get_preferred_desk_home(user: str | None, role_names: list[str] | tuple[str, ...] | set[str] | None = None) -> str:
    workspace_name = get_preferred_workspace_name(user, role_names)
    return WORKSPACE_ROUTES.get(workspace_name, AIHR_DESK_HOME)


def get_preferred_workspace_name(user: str | None, role_names: list[str] | tuple[str, ...] | set[str] | None = None) -> str:
    return preferred_workspace_for_roles(role_names or _get_role_names(user))


def user_can_access_workspace_path(
    user: str | None,
    path: str | None,
    role_names: list[str] | tuple[str, ...] | set[str] | None = None,
) -> bool:
    normalized = (path or "").strip()
    workspace_name = ROUTE_TO_WORKSPACE.get(normalized)
    if not workspace_name:
        return True

    allowed_roles = set(WORKSPACE_ROLE_BINDINGS.get(workspace_name, []))
    current_roles = set(role_names or _get_role_names(user))
    if not allowed_roles:
        return True
    return bool(allowed_roles & current_roles)


def _get_role_names(user: str | None) -> list[str]:
    try:
        import frappe
    except ModuleNotFoundError:
        return []

    if not user or user == "Guest":
        return []
    return list(frappe.get_roles(user))


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
    navbar_settings = bootinfo.get("navbar_settings")
    if not navbar_settings:
        return

    settings_dropdown = list(getattr(navbar_settings, "settings_dropdown", None) or [])
    filtered_settings_dropdown = [
        item for item in settings_dropdown if item.get("item_label") != "View Website"
    ]
    if isinstance(navbar_settings, dict):
        navbar_settings["settings_dropdown"] = filtered_settings_dropdown
    else:
        navbar_settings.settings_dropdown = filtered_settings_dropdown


def redirect_desk_root() -> None:
    import frappe
    from werkzeug.routing import RequestRedirect

    request = getattr(frappe.local, "request", None)
    if not request or request.method not in {"GET", "HEAD"}:
        return

    current_user = getattr(frappe.session, "user", None)
    if getattr(request, "path", "") == "/" and is_probably_logged_in_system_user(
        current_user, getattr(request, "cookies", None)
    ):
        raise RequestRedirect(AIHR_DESK_HOME)

    target = normalize_desk_path(getattr(request, "path", ""), current_user)
    if target and target != request.path:
        raise RequestRedirect(target)
