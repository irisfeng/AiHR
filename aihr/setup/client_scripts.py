from __future__ import annotations

from pathlib import Path


def ensure_client_scripts() -> None:
    import frappe

    for spec in CLIENT_SCRIPTS:
        script = _load_script(spec["script_path"])
        existing = frappe.db.exists("Client Script", spec["name"])
        doc = frappe.get_doc("Client Script", existing) if existing else frappe.new_doc("Client Script")
        doc.name = spec["name"]
        doc.dt = spec["dt"]
        doc.view = "Form"
        doc.module = "Recruitment Intelligence"
        doc.enabled = 1
        doc.script = script
        doc.save(ignore_permissions=True)

    frappe.clear_cache()


def _load_script(relative_path: str) -> str:
    import frappe

    return Path(frappe.get_app_path("aihr", *relative_path.split("/"))).read_text(encoding="utf-8")


CLIENT_SCRIPTS = [
    {
        "name": "AIHR Job Applicant Form",
        "dt": "Job Applicant",
        "script_path": "public/js/job_applicant.js",
    },
    {
        "name": "AIHR Job Requisition Form",
        "dt": "Job Requisition",
        "script_path": "public/js/job_requisition.js",
    },
    {
        "name": "AIHR Job Opening Form",
        "dt": "Job Opening",
        "script_path": "public/js/job_opening.js",
    },
]
