from __future__ import annotations

AIHR_DEPARTMENT_NAMES = [
    "市场部",
    "销售部",
    "销售划小单元",
    "运营中心",
    "政务热线运营中心",
    "财务部",
    "人事部",
    "交付中心",
    "产研中心",
]

LEGACY_DEPARTMENT_LABEL_MAP = {
    "People": "人事部",
}


def ensure_aihr_departments() -> None:
    import frappe

    company_names = frappe.get_all("Company", pluck="name") or []
    for company_name in company_names:
        for department_name in AIHR_DEPARTMENT_NAMES:
            _ensure_department(company_name, department_name)
        _normalize_legacy_departments(company_name)
        _ensure_demo_manager_department_scope(company_name)


def _ensure_department(company_name: str, department_name: str) -> None:
    import frappe

    existing = frappe.db.get_value(
        "Department",
        {"department_name": department_name, "company": company_name},
        "name",
    )
    if existing:
        doc = frappe.get_doc("Department", existing)
        updates = {}
        if getattr(doc, "parent_department", None):
            updates["parent_department"] = ""
        if updates:
            frappe.db.set_value("Department", existing, updates, update_modified=False)
        return

    doc = frappe.new_doc("Department")
    doc.department_name = department_name
    doc.company = company_name
    if hasattr(doc, "parent_department"):
        doc.parent_department = ""
    doc.save(ignore_permissions=True)


def _normalize_legacy_departments(company_name: str) -> None:
    import frappe

    for legacy_label, target_label in LEGACY_DEPARTMENT_LABEL_MAP.items():
        legacy_department = frappe.db.get_value(
            "Department",
            {"department_name": legacy_label, "company": company_name},
            "name",
        )
        target_department = frappe.db.get_value(
            "Department",
            {"department_name": target_label, "company": company_name},
            "name",
        )
        if not legacy_department or not target_department or legacy_department == target_department:
            continue

        for doctype in ("Employee", "Job Requisition", "Job Opening", "Employee Onboarding"):
            frappe.db.sql(
                f"update `tab{doctype}` set department = %s where department = %s",
                (target_department, legacy_department),
            )

        frappe.db.sql(
            """
            update `tabUser Permission`
            set for_value = %s
            where allow = 'Department' and for_value = %s
            """,
            (target_department, legacy_department),
        )


def _ensure_demo_manager_department_scope(company_name: str) -> None:
    import frappe

    user_id = "manager.demo@aihr.local"
    if not frappe.db.exists("User", user_id):
        return

    target_department = frappe.db.get_value(
        "Department",
        {"department_name": "人事部", "company": company_name},
        "name",
    )
    if not target_department:
        return

    employee_name = frappe.db.get_value("Employee", {"user_id": user_id}, "name")
    if employee_name and frappe.db.get_value("Employee", employee_name, "department") != target_department:
        frappe.db.set_value("Employee", employee_name, "department", target_department, update_modified=False)

    existing_permission = frappe.db.exists(
        "User Permission",
        {"user": user_id, "allow": "Department", "for_value": target_department},
    )
    if not existing_permission:
        doc = frappe.get_doc(
            {
                "doctype": "User Permission",
                "user": user_id,
                "allow": "Department",
                "for_value": target_department,
                "apply_to_all_doctypes": 1,
                "hide_descendants": 0,
                "is_default": 1,
            }
        )
        doc.insert(ignore_permissions=True)
