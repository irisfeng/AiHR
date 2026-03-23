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

DEMO_MANAGER_ACCOUNTS = [
    {
        "user_id": "manager.demo@aihr.local",
        "first_name": "Hiring",
        "last_name": "Manager",
        "department_name": "人事部",
        "designation_name": "HRBP",
        "password": "AIHRDemo!2026",
    },
    {
        "user_id": "delivery.manager@aihr.local",
        "first_name": "交付中心",
        "last_name": "经理",
        "department_name": "交付中心",
        "designation_name": "交付中心经理",
        "password": "AIHRDemo!2026",
    },
]

DEMO_HR_ACCOUNTS = [
    {
        "user_id": "hr.demo@aihr.local",
        "first_name": "HR",
        "last_name": "专员",
        "department_name": "人事部",
        "designation_name": "HR 招聘专员",
        "password": "AIHRDemo!2026",
        "scope_to_department": False,
    },
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
        _ensure_demo_manager_accounts(company_name)
        _ensure_demo_hr_accounts(company_name)


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


def _ensure_demo_manager_accounts(company_name: str) -> None:
    for profile in DEMO_MANAGER_ACCOUNTS:
        _ensure_demo_manager_account(company_name, profile)


def _ensure_demo_hr_accounts(company_name: str) -> None:
    for profile in DEMO_HR_ACCOUNTS:
        _ensure_demo_manager_account(company_name, profile)


def _ensure_designation(name: str) -> None:
    import frappe

    if frappe.db.exists("Designation", {"designation_name": name}):
        return
    doc = frappe.new_doc("Designation")
    doc.designation_name = name
    doc.save(ignore_permissions=True)


def _ensure_demo_manager_account(company_name: str, profile: dict[str, str]) -> None:
    import frappe

    user_id = profile["user_id"]
    if not frappe.db.exists("User", user_id):
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": user_id,
                "first_name": profile["first_name"],
                "last_name": profile["last_name"],
                "new_password": profile["password"],
                "send_welcome_email": 0,
            }
        )
        user.insert(ignore_permissions=True)

    target_department = frappe.db.get_value(
        "Department",
        {"department_name": profile["department_name"], "company": company_name},
        "name",
    )
    if not target_department:
        return

    _ensure_designation(profile["designation_name"])

    employee_name = frappe.db.get_value("Employee", {"user_id": user_id}, "name")
    if employee_name:
        updates = {}
        if frappe.db.get_value("Employee", employee_name, "department") != target_department:
            updates["department"] = target_department
        if frappe.db.get_value("Employee", employee_name, "designation") != profile["designation_name"]:
            updates["designation"] = profile["designation_name"]
        if updates:
            frappe.db.set_value("Employee", employee_name, updates, update_modified=False)
    else:
        employee = frappe.get_doc(
            {
                "doctype": "Employee",
                "naming_series": "HR-EMP-",
                "first_name": profile["first_name"],
                "last_name": profile["last_name"],
                "company": company_name,
                "department": target_department,
                "designation": profile["designation_name"],
                "user_id": user_id,
                "date_of_birth": "1990-05-08",
                "date_of_joining": frappe.utils.today(),
                "gender": "Female",
                "company_email": user_id,
                "prefered_contact_email": "Company Email",
                "prefered_email": user_id,
                "status": "Active",
            }
        )
        employee.insert(ignore_permissions=True)

    if profile.get("scope_to_department", True):
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
    else:
        frappe.db.sql(
            """
            delete from `tabUser Permission`
            where user = %s and allow = 'Department'
            """,
            (user_id,),
        )
