app_name = "aihr"
app_title = "AIHR"
app_publisher = "AIHR Team"
app_description = "AI-first recruitment workflow extension for Frappe HR"
app_email = "platform@example.com"
app_license = "GPL-3.0-or-later"
required_apps = ["frappe/hrms"]
app_home = "/app/aihr-hiring-hq"
app_logo_url = "/assets/aihr/images/aihr-logo.svg"

app_include_css = ["/assets/aihr/css/aihr_desk.css"]
app_include_js = ["/assets/aihr/js/aihr_desk.js"]

web_include_css = ["/assets/aihr/css/aihr_login.css"]
web_include_js = ["/assets/aihr/js/aihr_login.js"]

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
extend_bootinfo = ["aihr.setup.navigation.extend_bootinfo"]
before_request = ["aihr.setup.navigation.redirect_desk_root"]

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
    "Interview": {
        "validate": "aihr.events.recruitment.sync_interview_ops",
    },
    "Job Offer": {
        "validate": "aihr.events.recruitment.sync_job_offer_ops",
    },
    "Interview Feedback": {
        "validate": "aihr.events.recruitment.sync_interview_feedback_defaults",
        "on_submit": "aihr.events.recruitment.apply_interview_feedback_result",
    },
    "Employee Onboarding": {
        "validate": "aihr.events.recruitment.sync_employee_onboarding_defaults",
    },
}
