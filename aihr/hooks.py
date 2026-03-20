app_name = "aihr"
app_title = "AIHR"
app_publisher = "AIHR Team"
app_description = "AI-first recruitment workflow extension for Frappe HR"
app_email = "platform@example.com"
app_license = "GPL-3.0-or-later"
required_apps = ["frappe/hrms"]
app_home = "/app/aihr-hiring-hq"

add_to_apps_screen = [
    {
        "name": "aihr",
        "logo": "/assets/aihr/images/aihr-logo.svg",
        "title": "AIHR",
        "route": "/app/aihr-hiring-hq",
    }
]

after_install = "aihr.install.after_install"
after_migrate = "aihr.install.after_migrate"

doc_events = {
    "Job Requisition": {
        "validate": "aihr.events.recruitment.sync_job_requisition_brief",
    },
    "Job Opening": {
        "validate": "aihr.events.recruitment.sync_job_opening_pack",
    },
    "Job Applicant": {
        "after_insert": "aihr.events.recruitment.auto_screen_job_applicant_after_insert",
        "on_update": "aihr.events.recruitment.auto_screen_job_applicant_on_update",
    },
}
