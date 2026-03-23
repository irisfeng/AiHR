import unittest

from aihr.setup.access import (
    AIHR_HIRING_MANAGER_ROLE,
    DOCTYPE_PERMISSION_BLUEPRINT,
    HR_MANAGER_ROLE,
    HR_USER_ROLE,
    INTERVIEWER_ROLE,
    SYSTEM_MANAGER_ROLE,
    WORKSPACE_ROLE_BINDINGS,
)
from aihr.setup.departments import DEMO_HR_ACCOUNTS, DEMO_MANAGER_ACCOUNTS
from aihr.setup.workspace import (
    INTERVIEWER_WORKSPACE_NAME,
    MANAGER_WORKSPACE_NAME,
    WORKSPACE_NAME,
)


class AccessBlueprintTests(unittest.TestCase):
    def test_workspace_role_bindings_are_scoped(self):
        self.assertEqual(
            WORKSPACE_ROLE_BINDINGS[WORKSPACE_NAME],
            [HR_USER_ROLE, HR_MANAGER_ROLE, SYSTEM_MANAGER_ROLE],
        )
        self.assertEqual(
            WORKSPACE_ROLE_BINDINGS[MANAGER_WORKSPACE_NAME],
            [AIHR_HIRING_MANAGER_ROLE, HR_MANAGER_ROLE, SYSTEM_MANAGER_ROLE],
        )
        self.assertEqual(
            WORKSPACE_ROLE_BINDINGS[INTERVIEWER_WORKSPACE_NAME],
            [INTERVIEWER_ROLE, HR_USER_ROLE, HR_MANAGER_ROLE, SYSTEM_MANAGER_ROLE],
        )

    def test_job_requisition_permission_fix_is_defined(self):
        requisition_permissions = DOCTYPE_PERMISSION_BLUEPRINT["Job Requisition"]
        self.assertEqual(requisition_permissions[HR_USER_ROLE]["create"], 1)
        self.assertEqual(requisition_permissions[HR_MANAGER_ROLE]["write"], 1)
        self.assertEqual(requisition_permissions[AIHR_HIRING_MANAGER_ROLE]["create"], 1)

    def test_manager_workspace_related_doctypes_are_exposed_to_hiring_manager(self):
        for doctype in ("Job Opening", "Job Applicant", "AI Screening", "Interview", "Interview Feedback", "Job Offer"):
            self.assertIn(AIHR_HIRING_MANAGER_ROLE, DOCTYPE_PERMISSION_BLUEPRINT[doctype])
            self.assertEqual(DOCTYPE_PERMISSION_BLUEPRINT[doctype][AIHR_HIRING_MANAGER_ROLE]["read"], 1)

    def test_interviewer_workspace_supporting_doctypes_are_readable(self):
        self.assertEqual(DOCTYPE_PERMISSION_BLUEPRINT["Job Applicant"][INTERVIEWER_ROLE]["read"], 1)
        self.assertEqual(DOCTYPE_PERMISSION_BLUEPRINT["AI Screening"][INTERVIEWER_ROLE]["read"], 1)

    def test_demo_manager_seed_accounts_are_available_for_role_assignment(self):
        self.assertIn("manager.demo@aihr.local", {item["user_id"] for item in DEMO_MANAGER_ACCOUNTS})
        self.assertIn("delivery.manager@aihr.local", {item["user_id"] for item in DEMO_MANAGER_ACCOUNTS})
        self.assertIn("hr.demo@aihr.local", {item["user_id"] for item in DEMO_HR_ACCOUNTS})


if __name__ == "__main__":
    unittest.main()
