from __future__ import annotations


def ensure_title_fields() -> None:
    import frappe
    from frappe.custom.doctype.property_setter.property_setter import make_property_setter

    specs = [
        ("Job Opening", "job_title"),
        ("Job Requisition", "designation"),
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
