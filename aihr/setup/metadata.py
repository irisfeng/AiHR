from __future__ import annotations


def ensure_title_fields() -> None:
    import frappe
    from frappe.custom.doctype.property_setter.property_setter import make_property_setter

    specs = [
        ("Job Opening", "job_title"),
        ("Job Requisition", "aihr_job_title"),
        ("Job Applicant", "applicant_name"),
        ("AI Screening", "aihr_candidate_name_snapshot"),
    ]

    for doctype, fieldname in specs:
        current = frappe.db.get_value("DocType", doctype, "title_field")
        if current == fieldname:
            continue
        make_property_setter(
            doctype,
            None,
            "title_field",
            fieldname,
            "Data",
            for_doctype=True,
        )

    frappe.clear_cache()


def ensure_requisition_field_presentation() -> None:
    import frappe
    from frappe.custom.doctype.property_setter.property_setter import make_property_setter

    specs = [
        ("Job Requisition", "designation", "hidden", 1, "Check"),
        ("Job Requisition", "requested_by_designation", "hidden", 1, "Check"),
    ]

    for doctype, fieldname, property_name, value, property_type in specs:
        current = frappe.db.get_value(
            "Property Setter",
            {
                "doc_type": doctype,
                "field_name": fieldname,
                "property": property_name,
            },
            "value",
        )
        if str(current) == str(value):
            continue
        make_property_setter(
            doctype,
            fieldname,
            property_name,
            value,
            property_type,
        )

    frappe.clear_cache()


def sync_job_requisition_display_fields() -> None:
    import frappe

    requisitions = frappe.get_all(
        "Job Requisition",
        fields=["name", "designation", "requested_by", "aihr_job_title", "aihr_requested_by_title"],
    )

    for requisition in requisitions:
        updates = {}
        title = (requisition.get("aihr_job_title") or requisition.get("designation") or "").strip()
        if title and title != (requisition.get("aihr_job_title") or ""):
            updates["aihr_job_title"] = title

        requester = requisition.get("requested_by")
        requester_title = ""
        if requester and frappe.db.exists("Employee", requester):
            requester_title = frappe.db.get_value("Employee", requester, "designation") or ""
        if requester_title and requester_title != (requisition.get("aihr_requested_by_title") or ""):
            updates["aihr_requested_by_title"] = requester_title

        if updates:
            frappe.db.set_value("Job Requisition", requisition["name"], updates, update_modified=False)

    frappe.clear_cache()


def sync_ai_screening_display_snapshots() -> None:
    import frappe

    from aihr.services.recruitment_ops import build_opening_display_title

    screenings = frappe.get_all(
        "AI Screening",
        fields=[
            "name",
            "job_applicant",
            "job_opening",
            "aihr_candidate_name_snapshot",
            "aihr_opening_title_snapshot",
        ],
    )

    for screening in screenings:
        candidate_name = screening.get("aihr_candidate_name_snapshot") or ""
        opening_title = screening.get("aihr_opening_title_snapshot") or ""

        if not candidate_name and screening.get("job_applicant"):
            candidate_name = (
                frappe.db.get_value("Job Applicant", screening["job_applicant"], "applicant_name")
                or screening["job_applicant"]
            )

        if not opening_title and screening.get("job_opening"):
            if frappe.db.exists("Job Opening", screening["job_opening"]):
                opening_title = build_opening_display_title(
                    frappe.get_doc("Job Opening", screening["job_opening"])
                )
            else:
                opening_title = screening["job_opening"]

        updates = {}
        if candidate_name and candidate_name != screening.get("aihr_candidate_name_snapshot"):
            updates["aihr_candidate_name_snapshot"] = candidate_name
        if opening_title and opening_title != screening.get("aihr_opening_title_snapshot"):
            updates["aihr_opening_title_snapshot"] = opening_title

        if updates:
            frappe.db.set_value("AI Screening", screening["name"], updates, update_modified=False)

    frappe.clear_cache()


def normalize_imported_job_applicants() -> None:
    import frappe

    imported_applicants = frappe.get_all(
        "Job Applicant",
        filters={"aihr_resume_intake_batch": ["is", "set"]},
        fields=["name", "source", "source_name", "employee_referral"],
    )

    for applicant in imported_applicants:
        updates = {}
        if applicant.get("source"):
            updates["source"] = None
        if applicant.get("source_name"):
            updates["source_name"] = None
        if applicant.get("employee_referral"):
            updates["employee_referral"] = None

        if updates:
            frappe.db.set_value("Job Applicant", applicant["name"], updates, update_modified=False)

    frappe.clear_cache()
