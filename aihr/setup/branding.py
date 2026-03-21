from __future__ import annotations

from aihr.setup.workspace import AIHR_WORKSPACE_LABELS, AIHR_WORKSPACE_NAMES, WORKSPACE_NAME

AIHR_APP_NAME = "AIHR"
AIHR_APP_SLUG = "aihr"
AIHR_LOGO_PATH = "/assets/aihr/images/aihr-logo.svg"
AIHR_PUBLIC_BRAND_HTML = (
    '<span class="aihr-web-brand" '
    'style="display:inline-flex;align-items:center;gap:10px;font-weight:700;color:#0f172a;">'
    f'<img src="{AIHR_LOGO_PATH}" alt="AIHR" style="height:28px;width:auto;" />'
    '<span>AIHR</span>'
    "</span>"
)

STANDARD_WORKSPACES_TO_REPLACE = {
    "",
    "Home",
    "HR",
    "Accounting",
    "Buying",
    "Selling",
    "Stock",
    "Assets",
    "Manufacturing",
    "Quality",
    "Projects",
    "Support",
    "Users",
    "Website",
    "Payroll",
    "CRM",
    "Tools",
    "ERPNext Settings",
    "ERPNext Integrations",
    "Integrations",
    "Build",
}

STANDARD_APPS_TO_REPLACE = {"", "frappe", "erpnext", "hrms"}


def ensure_aihr_branding() -> None:
    import frappe

    _ensure_system_settings()
    _ensure_website_settings()
    _ensure_navbar_settings()
    _ensure_workspace_visibility()
    _ensure_user_defaults()
    frappe.clear_cache()


def is_aihr_workspace(workspace_name: str | None, title: str | None = None) -> bool:
    normalized_name = (workspace_name or "").strip()
    normalized_title = (title or "").strip()
    return normalized_name in AIHR_WORKSPACE_NAMES or normalized_title in AIHR_WORKSPACE_LABELS | AIHR_WORKSPACE_NAMES


def should_reset_default_workspace(default_workspace: str | None) -> bool:
    normalized = (default_workspace or "").strip()
    return normalized in STANDARD_WORKSPACES_TO_REPLACE or not normalized


def should_reset_default_app(default_app: str | None) -> bool:
    normalized = (default_app or "").strip().lower()
    return normalized in STANDARD_APPS_TO_REPLACE or not normalized


def _ensure_system_settings() -> None:
    import frappe

    _set_single_value("System Settings", "app_name", AIHR_APP_NAME)
    _set_single_value("System Settings", "default_app", AIHR_APP_SLUG)


def _ensure_website_settings() -> None:
    _set_single_value("Website Settings", "app_name", AIHR_APP_NAME)
    _set_single_value("Website Settings", "app_logo", AIHR_LOGO_PATH)
    _set_single_value("Website Settings", "title_prefix", AIHR_APP_NAME)
    _set_single_value("Website Settings", "brand_html", AIHR_PUBLIC_BRAND_HTML)
    _set_single_value("Website Settings", "show_footer_on_login", 0)


def _ensure_navbar_settings() -> None:
    _set_single_value("Navbar Settings", "app_logo", AIHR_LOGO_PATH)


def _ensure_workspace_visibility() -> None:
    import frappe

    workspaces = frappe.get_all("Workspace", filters={"public": 1}, fields=["name", "title", "is_hidden"])
    for workspace in workspaces:
        should_show = is_aihr_workspace(workspace.get("name"), workspace.get("title"))
        desired_hidden = 0 if should_show else 1
        if int(workspace.get("is_hidden") or 0) != desired_hidden:
            doc = frappe.get_doc("Workspace", workspace.get("name"))
            doc.flags.ignore_links = True
            doc.flags.ignore_validate = True
            doc.is_hidden = desired_hidden
            doc.save(ignore_permissions=True)


def _ensure_user_defaults() -> None:
    import frappe

    users = frappe.get_all(
        "User",
        filters={"enabled": 1, "user_type": "System User"},
        fields=["name", "default_workspace", "default_app"],
    )
    for user in users:
        updates: dict[str, str] = {}
        if should_reset_default_workspace(user.get("default_workspace")):
            updates["default_workspace"] = WORKSPACE_NAME
        if should_reset_default_app(user.get("default_app")):
            updates["default_app"] = AIHR_APP_SLUG
        if updates:
            frappe.db.set_value("User", user.get("name"), updates, update_modified=False)


def _set_single_value(doctype: str, fieldname: str, value) -> None:
    import frappe

    current = frappe.db.get_single_value(doctype, fieldname)
    if current != value:
        frappe.db.set_single_value(doctype, fieldname, value)
