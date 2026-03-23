app_name = "aihr"
app_title = "AIHR"
app_publisher = "AIHR Team"
app_description = "AI-first recruitment workflow extension for Frappe HR"
app_email = "platform@example.com"
app_license = "GPL-3.0-or-later"
required_apps = ["frappe/hrms"]
app_home = "/app"
app_logo_url = "/assets/aihr/images/aihr-logo.svg"

app_include_css = ["/assets/aihr/css/aihr_desk_v2.css"]
app_include_js = ["/assets/aihr/js/aihr_desk_v2.js"]

LOGIN_ASSET_VERSION = "20260321-login-v5"

web_include_css = [f"/assets/aihr/css/aihr_login.css?v={LOGIN_ASSET_VERSION}"]
web_include_js = [f"/assets/aihr/js/aihr_login.js?v={LOGIN_ASSET_VERSION}"]

add_to_apps_screen = [
    {
        "name": "aihr",
        "logo": "/assets/aihr/images/aihr-logo.svg",
        "title": "AIHR",
        "route": "/app",
    }
]

after_install = "aihr.install.after_install"
after_migrate = "aihr.install.after_migrate"
extend_bootinfo = ["aihr.setup.navigation.extend_bootinfo"]
before_request = ["aihr.setup.navigation.redirect_desk_root"]

permission_query_conditions = {
    "Job Requisition": "aihr.permissions.get_job_requisition_query_condition",
    "Job Opening": "aihr.permissions.get_job_opening_query_condition",
    "Job Applicant": "aihr.permissions.get_job_applicant_query_condition",
    "AI Screening": "aihr.permissions.get_ai_screening_query_condition",
    "Interview": "aihr.permissions.get_interview_query_condition",
    "Interview Feedback": "aihr.permissions.get_interview_feedback_query_condition",
    "Job Offer": "aihr.permissions.get_job_offer_query_condition",
}

has_permission = {
    "Job Requisition": "aihr.permissions.has_job_requisition_permission",
    "Job Opening": "aihr.permissions.has_job_opening_permission",
    "Job Applicant": "aihr.permissions.has_job_applicant_permission",
    "AI Screening": "aihr.permissions.has_ai_screening_permission",
    "Interview": "aihr.permissions.has_interview_permission",
    "Interview Feedback": "aihr.permissions.has_interview_feedback_permission",
    "Job Offer": "aihr.permissions.has_job_offer_permission",
}

doc_events = {
    "Job Requisition": {
        "validate": "aihr.events.recruitment.sync_job_requisition_brief",
        "on_update": "aihr.events.recruitment.sync_job_requisition_workflow_state",
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
