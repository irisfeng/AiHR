import unittest

from aihr.setup.custom_fields import get_custom_fields


class RequisitionFormTests(unittest.TestCase):
    def test_job_requisition_has_frontend_job_title_field(self):
        fields = {field["fieldname"]: field for field in get_custom_fields()["Job Requisition"]}
        self.assertIn("aihr_job_title", fields)
        self.assertEqual(fields["aihr_job_title"]["fieldtype"], "Data")
        self.assertEqual(fields["aihr_job_title"]["reqd"], 1)

    def test_job_requisition_has_readonly_requester_title_field(self):
        fields = {field["fieldname"]: field for field in get_custom_fields()["Job Requisition"]}
        self.assertIn("aihr_requested_by_title", fields)
        self.assertEqual(fields["aihr_requested_by_title"]["fieldtype"], "Data")
        self.assertEqual(fields["aihr_requested_by_title"]["read_only"], 1)

    def test_job_requisition_has_frontend_role_description_field(self):
        fields = {field["fieldname"]: field for field in get_custom_fields()["Job Requisition"]}
        self.assertIn("aihr_role_description_input", fields)
        self.assertEqual(fields["aihr_role_description_input"]["fieldtype"], "Long Text")


if __name__ == "__main__":
    unittest.main()
