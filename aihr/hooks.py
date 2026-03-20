app_name = "aihr"
app_title = "AIHR"
app_publisher = "AIHR Team"
app_description = "AI-first recruitment workflow extension for Frappe HR"
app_email = "platform@example.com"
app_license = "GPL-3.0-or-later"
required_apps = ["frappe/hrms"]
app_home = "/app/job-requisition"

add_to_apps_screen = [
    {
        "name": "aihr",
        "logo": "/assets/frappe/images/frappe-framework-logo.svg",
        "title": "AIHR",
        "route": "/app/job-requisition",
    }
]

after_install = "aihr.install.after_install"
after_migrate = "aihr.install.after_migrate"

