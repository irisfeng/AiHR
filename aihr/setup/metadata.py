from __future__ import annotations


def ensure_title_fields() -> None:
    import frappe
    from frappe.custom.doctype.property_setter.property_setter import make_property_setter

    specs = [
        ("Job Opening", "job_title"),
        ("Job Requisition", "designation"),
        ("Job Applicant", "applicant_name"),
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
