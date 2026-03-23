from __future__ import annotations

from aihr.setup.departments import DEMO_HR_ACCOUNTS, DEMO_MANAGER_ACCOUNTS
from aihr.setup.workspace import (
    INTERVIEWER_WORKSPACE_NAME,
    MANAGER_WORKSPACE_NAME,
    WORKSPACE_NAME,
)

SYSTEM_MANAGER_ROLE = "System Manager"
HR_USER_ROLE = "HR User"
HR_MANAGER_ROLE = "HR Manager"
INTERVIEWER_ROLE = "Interviewer"
AIHR_HIRING_MANAGER_ROLE = "AIHR Hiring Manager"

AIHR_ROLES = {
    AIHR_HIRING_MANAGER_ROLE,
}

WORKSPACE_ROLE_BINDINGS = {
    WORKSPACE_NAME: [HR_USER_ROLE, HR_MANAGER_ROLE, SYSTEM_MANAGER_ROLE],
    MANAGER_WORKSPACE_NAME: [AIHR_HIRING_MANAGER_ROLE, HR_MANAGER_ROLE, SYSTEM_MANAGER_ROLE],
    INTERVIEWER_WORKSPACE_NAME: [INTERVIEWER_ROLE, HR_USER_ROLE, HR_MANAGER_ROLE, SYSTEM_MANAGER_ROLE],
}

DOCTYPE_PERMISSION_BLUEPRINT: dict[str, dict[str, dict[str, int]]] = {
    "Designation": {
        HR_USER_ROLE: {"read": 1, "write": 1, "create": 1, "report": 1, "select": 1},
        HR_MANAGER_ROLE: {"read": 1, "write": 1, "create": 1, "delete": 1, "report": 1, "select": 1},
        AIHR_HIRING_MANAGER_ROLE: {"read": 1, "write": 1, "create": 1, "report": 1, "select": 1},
    },
    "Department": {
        HR_USER_ROLE: {"read": 1, "report": 1, "select": 1},
        HR_MANAGER_ROLE: {"read": 1, "report": 1, "select": 1},
        AIHR_HIRING_MANAGER_ROLE: {"read": 1, "report": 1, "select": 1},
    },
    "Job Requisition": {
        HR_USER_ROLE: {"read": 1, "write": 1, "create": 1, "report": 1},
        HR_MANAGER_ROLE: {"read": 1, "write": 1, "create": 1, "delete": 1, "report": 1},
        AIHR_HIRING_MANAGER_ROLE: {"read": 1, "write": 1, "create": 1, "report": 1},
    },
    "Job Opening": {
        HR_MANAGER_ROLE: {"read": 1, "write": 1, "create": 1, "delete": 1, "report": 1},
        AIHR_HIRING_MANAGER_ROLE: {"read": 1, "report": 1},
    },
    "Job Applicant": {
        HR_MANAGER_ROLE: {"read": 1, "write": 1, "create": 1, "delete": 1, "report": 1},
        AIHR_HIRING_MANAGER_ROLE: {"read": 1, "report": 1},
        INTERVIEWER_ROLE: {"read": 1, "report": 1},
    },
    "AI Screening": {
        AIHR_HIRING_MANAGER_ROLE: {"read": 1, "report": 1},
        INTERVIEWER_ROLE: {"read": 1, "report": 1},
    },
    "Interview": {
        AIHR_HIRING_MANAGER_ROLE: {"read": 1, "report": 1},
    },
    "Interview Feedback": {
        AIHR_HIRING_MANAGER_ROLE: {"read": 1, "report": 1},
    },
    "Job Offer": {
        HR_MANAGER_ROLE: {"read": 1, "write": 1, "create": 1, "submit": 1, "delete": 1, "report": 1},
        AIHR_HIRING_MANAGER_ROLE: {"read": 1, "report": 1},
    },
    "Employee Onboarding": {
        HR_USER_ROLE: {"read": 1, "write": 1, "create": 1, "submit": 1, "report": 1},
    },
}

DEFAULT_WORKSPACE_BY_ROLE = {
    AIHR_HIRING_MANAGER_ROLE: MANAGER_WORKSPACE_NAME,
    INTERVIEWER_ROLE: INTERVIEWER_WORKSPACE_NAME,
    HR_USER_ROLE: WORKSPACE_NAME,
    HR_MANAGER_ROLE: WORKSPACE_NAME,
    SYSTEM_MANAGER_ROLE: WORKSPACE_NAME,
}


def ensure_aihr_access() -> None:
    import frappe

    _ensure_roles()
    _ensure_workspace_roles()
    _ensure_doctype_permissions()
    _assign_demo_roles()
    frappe.clear_cache()


def preferred_workspace_for_roles(role_names: list[str] | set[str] | tuple[str, ...]) -> str:
    normalized = {str(role).strip() for role in (role_names or []) if str(role).strip()}

    if HR_MANAGER_ROLE in normalized or HR_USER_ROLE in normalized or SYSTEM_MANAGER_ROLE in normalized:
        return WORKSPACE_NAME
    if AIHR_HIRING_MANAGER_ROLE in normalized:
        return MANAGER_WORKSPACE_NAME
    if INTERVIEWER_ROLE in normalized:
        return INTERVIEWER_WORKSPACE_NAME
    return WORKSPACE_NAME


def _ensure_roles() -> None:
    import frappe

    for role_name in sorted(AIHR_ROLES):
        existing = frappe.db.exists("Role", role_name)
        doc = frappe.get_doc("Role", existing) if existing else frappe.new_doc("Role")
        doc.role_name = role_name
        doc.is_custom = 1
        doc.desk_access = 1
        if role_name == AIHR_HIRING_MANAGER_ROLE:
            doc.home_page = "/app/aihr-manager-review"
        doc.save(ignore_permissions=True)


def _ensure_workspace_roles() -> None:
    import frappe

    for workspace_name, roles in WORKSPACE_ROLE_BINDINGS.items():
        existing = frappe.db.exists("Workspace", workspace_name)
        if not existing:
            continue

        doc = frappe.get_doc("Workspace", existing)
        current_roles = [row.role for row in getattr(doc, "roles", []) if getattr(row, "role", None)]
        if current_roles == roles:
            continue

        doc.set("roles", [{"role": role_name} for role_name in roles])
        doc.flags.ignore_links = True
        doc.flags.ignore_validate = True
        doc.save(ignore_permissions=True)


def _ensure_doctype_permissions() -> None:
    import frappe
    from frappe.permissions import add_permission, update_permission_property

    for doctype, role_matrix in DOCTYPE_PERMISSION_BLUEPRINT.items():
        for role_name, permissions in role_matrix.items():
            add_permission(doctype, role_name)
            for ptype, value in permissions.items():
                update_permission_property(doctype, role_name, 0, ptype, value, validate=False)
        frappe.clear_cache(doctype=doctype)


def _assign_demo_roles() -> None:
    import frappe

    role_map = {
        **{profile["user_id"]: (AIHR_HIRING_MANAGER_ROLE, "Employee") for profile in DEMO_MANAGER_ACCOUNTS},
        **{profile["user_id"]: (HR_USER_ROLE, HR_MANAGER_ROLE, "Employee") for profile in DEMO_HR_ACCOUNTS},
    }

    for user_id, role_names in role_map.items():
        if not frappe.db.exists("User", user_id):
            continue

        user = frappe.get_doc("User", user_id)
        existing_roles = {row.role for row in getattr(user, "roles", []) if getattr(row, "role", None)}
        updated = False

        for role_name in role_names:
            if role_name not in existing_roles:
                user.append("roles", {"role": role_name})
                updated = True

        if updated:
            user.save(ignore_permissions=True)
