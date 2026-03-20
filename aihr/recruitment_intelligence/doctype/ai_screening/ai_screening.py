import frappe
from frappe.model.document import Document


class AIScreening(Document):
    def validate(self):
        if self.job_applicant and not self.job_opening:
            self.job_opening = frappe.db.get_value("Job Applicant", self.job_applicant, "job_title")

