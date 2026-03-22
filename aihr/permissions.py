from __future__ import annotations

from aihr.setup.access import AIHR_HIRING_MANAGER_ROLE, HR_MANAGER_ROLE, HR_USER_ROLE, SYSTEM_MANAGER_ROLE

UNRESTRICTED_ROLES = {SYSTEM_MANAGER_ROLE, HR_USER_ROLE, HR_MANAGER_ROLE}


def get_job_requisition_query_condition(user: str | None = None) -> str | None:
    return _direct_department_condition("`tabJob Requisition`", "department", user)


def has_job_requisition_permission(doc, user: str | None = None, permission_type: str | None = None) -> bool | None:
    return _has_department_permission(doc, user, resolver=_resolve_direct_department, doctype="Job Requisition")


def get_job_opening_query_condition(user: str | None = None) -> str | None:
    return _direct_department_condition("`tabJob Opening`", "department", user)


def has_job_opening_permission(doc, user: str | None = None, permission_type: str | None = None) -> bool | None:
    return _has_department_permission(doc, user, resolver=_resolve_direct_department, doctype="Job Opening")


def get_job_applicant_query_condition(user: str | None = None) -> str | None:
    return _linked_opening_department_condition("`tabJob Applicant`", "job_title", user)


def has_job_applicant_permission(doc, user: str | None = None, permission_type: str | None = None) -> bool | None:
    return _has_department_permission(
        doc,
        user,
        resolver=lambda candidate: getattr(candidate, "job_title", None),
        target="opening",
        doctype="Job Applicant",
    )


def get_ai_screening_query_condition(user: str | None = None) -> str | None:
    departments = get_scoped_departments(user)
    if departments is None:
        return None
    if not departments:
        return "1=0"
    csv = _escaped_csv(departments)
    return (
        "((`tabAI Screening`.job_opening is not null "
        f"and exists (select 1 from `tabJob Opening` jo where jo.name = `tabAI Screening`.job_opening and jo.department in ({csv}))) "
        "or (`tabAI Screening`.job_opening is null "
        f"and exists (select 1 from `tabJob Applicant` ja inner join `tabJob Opening` jo on jo.name = ja.job_title where ja.name = `tabAI Screening`.job_applicant and jo.department in ({csv}))))"
    )


def has_ai_screening_permission(doc, user: str | None = None, permission_type: str | None = None) -> bool | None:
    return _has_department_permission(doc, user, resolver=_resolve_screening_opening, target="opening", doctype="AI Screening")


def get_interview_query_condition(user: str | None = None) -> str | None:
    departments = get_scoped_departments(user)
    if departments is None:
        return None
    if not departments:
        return "1=0"
    csv = _escaped_csv(departments)
    return (
        f"exists (select 1 from `tabJob Applicant` ja inner join `tabJob Opening` jo on jo.name = ja.job_title where ja.name = `tabInterview`.job_applicant and jo.department in ({csv}))"
    )


def has_interview_permission(doc, user: str | None = None, permission_type: str | None = None) -> bool | None:
    return _has_department_permission(doc, user, resolver=_resolve_interview_opening, target="opening", doctype="Interview")


def get_interview_feedback_query_condition(user: str | None = None) -> str | None:
    departments = get_scoped_departments(user)
    if departments is None:
        return None
    if not departments:
        return "1=0"
    csv = _escaped_csv(departments)
    return (
        "exists (select 1 from `tabInterview` i "
        "inner join `tabJob Applicant` ja on ja.name = i.job_applicant "
        "inner join `tabJob Opening` jo on jo.name = ja.job_title "
        f"where i.name = `tabInterview Feedback`.interview and jo.department in ({csv}))"
    )


def has_interview_feedback_permission(doc, user: str | None = None, permission_type: str | None = None) -> bool | None:
    return _has_department_permission(
        doc,
        user,
        resolver=_resolve_feedback_opening,
        target="opening",
        doctype="Interview Feedback",
    )


def get_job_offer_query_condition(user: str | None = None) -> str | None:
    departments = get_scoped_departments(user)
    if departments is None:
        return None
    if not departments:
        return "1=0"
    csv = _escaped_csv(departments)
    return (
        "exists (select 1 from `tabJob Applicant` ja "
        "inner join `tabJob Opening` jo on jo.name = ja.job_title "
        f"where ja.name = `tabJob Offer`.job_applicant and jo.department in ({csv}))"
    )


def has_job_offer_permission(doc, user: str | None = None, permission_type: str | None = None) -> bool | None:
    return _has_department_permission(doc, user, resolver=_resolve_offer_opening, target="opening", doctype="Job Offer")


def get_scoped_departments(user: str | None = None) -> list[str] | None:
    import frappe

    current_user = user or frappe.session.user
    if not _is_scoped_hiring_manager(current_user):
        return None

    explicit = [
        department
        for department in frappe.get_all(
            "User Permission",
            filters={"user": current_user, "allow": "Department"},
            pluck="for_value",
        )
        if frappe.db.exists("Department", department)
    ]
    if explicit:
        return sorted(set(explicit))

    employee_department = frappe.db.get_value("Employee", {"user_id": current_user}, "department")
    return [employee_department] if employee_department else []


def _is_scoped_hiring_manager(user: str | None) -> bool:
    import frappe

    if not user or user == "Guest":
        return False
    role_names = set(frappe.get_roles(user))
    return AIHR_HIRING_MANAGER_ROLE in role_names and not (role_names & UNRESTRICTED_ROLES)


def _direct_department_condition(table_name: str, fieldname: str, user: str | None = None) -> str | None:
    departments = get_scoped_departments(user)
    if departments is None:
        return None
    if not departments:
        return "1=0"
    return f"{table_name}.{fieldname} in ({_escaped_csv(departments)})"


def _linked_opening_department_condition(table_name: str, opening_fieldname: str, user: str | None = None) -> str | None:
    departments = get_scoped_departments(user)
    if departments is None:
        return None
    if not departments:
        return "1=0"
    return (
        "exists (select 1 from `tabJob Opening` jo "
        f"where jo.name = {table_name}.{opening_fieldname} and jo.department in ({_escaped_csv(departments)}))"
    )


def _escaped_csv(values: list[str]) -> str:
    import frappe

    return ", ".join(frappe.db.escape(value) for value in values)


def _has_department_permission(doc, user: str | None, resolver, target: str = "department", doctype: str | None = None) -> bool | None:
    departments = get_scoped_departments(user)
    if departments is None:
        return None
    if not doc:
        return bool(departments)

    document = _coerce_doc(doc, doctype)
    if not document:
        return False

    if target == "department":
        document_department = resolver(document)
    else:
        opening_name = resolver(document)
        document_department = _resolve_opening_department(opening_name)
    return bool(document_department and document_department in departments)


def _coerce_doc(doc, doctype: str | None):
    if isinstance(doc, str):
        import frappe

        if not doctype or not frappe.db.exists(doctype, doc):
            return None
        return frappe.get_cached_doc(doctype, doc)
    if isinstance(doc, dict):
        import frappe

        return frappe._dict(doc)
    return doc


def _resolve_direct_department(doc) -> str | None:
    return getattr(doc, "department", None)


def _resolve_opening_department(opening_name: str | None) -> str | None:
    import frappe

    if not opening_name:
        return None
    return frappe.db.get_value("Job Opening", opening_name, "department")


def _resolve_screening_opening(doc) -> str | None:
    import frappe

    opening_name = getattr(doc, "job_opening", None)
    if opening_name:
        return opening_name
    applicant_name = getattr(doc, "job_applicant", None)
    if not applicant_name:
        return None
    return frappe.db.get_value("Job Applicant", applicant_name, "job_title")


def _resolve_interview_opening(doc) -> str | None:
    import frappe

    opening_name = getattr(doc, "job_opening", None)
    if opening_name:
        return opening_name
    applicant_name = getattr(doc, "job_applicant", None)
    if not applicant_name:
        return None
    return frappe.db.get_value("Job Applicant", applicant_name, "job_title")


def _resolve_feedback_opening(doc) -> str | None:
    import frappe

    interview_name = getattr(doc, "interview", None)
    if not interview_name:
        return None
    opening_name = frappe.db.get_value("Interview", interview_name, "job_opening")
    if opening_name:
        return opening_name
    applicant_name = frappe.db.get_value("Interview", interview_name, "job_applicant")
    if not applicant_name:
        return None
    return frappe.db.get_value("Job Applicant", applicant_name, "job_title")


def _resolve_offer_opening(doc) -> str | None:
    import frappe

    applicant_name = getattr(doc, "job_applicant", None)
    if not applicant_name:
        return None
    return frappe.db.get_value("Job Applicant", applicant_name, "job_title")
