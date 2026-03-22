import types
import unittest
from unittest import mock

from aihr.permissions import (
    _has_department_permission,
    get_job_applicant_query_condition,
    get_job_requisition_query_condition,
    has_job_requisition_permission,
)


class PermissionScopeTests(unittest.TestCase):
    def test_job_requisition_query_condition_uses_direct_department_scope(self):
        with mock.patch("aihr.permissions.get_scoped_departments", return_value=["人事部 - AD"]), mock.patch(
            "aihr.permissions._escaped_csv", return_value="'人事部 - AD'"
        ):
            condition = get_job_requisition_query_condition("manager.demo@aihr.local")
        self.assertIn("`tabJob Requisition`.department in", condition)
        self.assertIn("人事部 - AD", condition)

    def test_job_applicant_query_condition_uses_opening_join(self):
        with mock.patch("aihr.permissions.get_scoped_departments", return_value=["人事部 - AD"]), mock.patch(
            "aihr.permissions._escaped_csv", return_value="'人事部 - AD'"
        ):
            condition = get_job_applicant_query_condition("manager.demo@aihr.local")
        self.assertIn("exists (select 1 from `tabJob Opening` jo", condition)
        self.assertIn("`tabJob Applicant`.job_title", condition)

    def test_direct_department_permission_accepts_matching_department(self):
        doc = types.SimpleNamespace(department="人事部 - AD")
        with mock.patch("aihr.permissions.get_scoped_departments", return_value=["人事部 - AD"]):
            allowed = _has_department_permission(doc, "manager.demo@aihr.local", resolver=lambda item: item.department)
        self.assertTrue(allowed)

    def test_direct_department_permission_rejects_other_department(self):
        doc = types.SimpleNamespace(department="市场部 - AD")
        with mock.patch("aihr.permissions.get_scoped_departments", return_value=["人事部 - AD"]):
            allowed = has_job_requisition_permission(doc, "manager.demo@aihr.local", "read")
        self.assertFalse(allowed)

    def test_docname_permission_loads_document_before_resolving_department(self):
        loaded_doc = types.SimpleNamespace(department="人事部 - AD")
        with mock.patch("aihr.permissions.get_scoped_departments", return_value=["人事部 - AD"]), mock.patch(
            "aihr.permissions._coerce_doc", return_value=loaded_doc
        ) as mocked_coerce:
            allowed = has_job_requisition_permission("HR-HIREQ-00001", "manager.demo@aihr.local", "read")
        mocked_coerce.assert_called_once_with("HR-HIREQ-00001", "Job Requisition")
        self.assertTrue(allowed)


if __name__ == "__main__":
    unittest.main()
