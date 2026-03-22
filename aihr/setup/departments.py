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


def ensure_aihr_departments() -> None:
    import frappe

    company_names = frappe.get_all("Company", pluck="name") or []
    for company_name in company_names:
        for department_name in AIHR_DEPARTMENT_NAMES:
            _ensure_department(company_name, department_name)


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
