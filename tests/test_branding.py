import unittest

from aihr.setup.access import (
    AIHR_HIRING_MANAGER_ROLE,
    HR_MANAGER_ROLE,
    HR_USER_ROLE,
    INTERVIEWER_ROLE,
    preferred_workspace_for_roles,
)
from aihr.setup.branding import (
    is_aihr_workspace,
    should_align_preferred_workspace,
    should_reset_default_app,
    should_reset_default_workspace,
    should_reset_language,
)
from aihr.setup.workspace import (
    INTERVIEWER_WORKSPACE_LABEL,
    INTERVIEWER_WORKSPACE_NAME,
    MANAGER_WORKSPACE_LABEL,
    MANAGER_WORKSPACE_NAME,
    WORKSPACE_BLOCK_LABEL,
    WORKSPACE_NAME,
)


class BrandingTests(unittest.TestCase):
    def test_detects_aihr_workspace(self):
        self.assertTrue(is_aihr_workspace(WORKSPACE_NAME, WORKSPACE_BLOCK_LABEL))
        self.assertTrue(is_aihr_workspace(MANAGER_WORKSPACE_NAME, MANAGER_WORKSPACE_LABEL))
        self.assertTrue(is_aihr_workspace(INTERVIEWER_WORKSPACE_NAME, INTERVIEWER_WORKSPACE_LABEL))
        self.assertTrue(is_aihr_workspace("Other", WORKSPACE_BLOCK_LABEL))
        self.assertFalse(is_aihr_workspace("Accounting", "Accounting"))

    def test_resets_standard_workspace_defaults(self):
        self.assertTrue(should_reset_default_workspace(None))
        self.assertTrue(should_reset_default_workspace("Home"))
        self.assertTrue(should_reset_default_workspace("Accounting"))
        self.assertFalse(should_reset_default_workspace(WORKSPACE_NAME))

    def test_aligns_existing_aihr_workspace_to_role_specific_home(self):
        self.assertTrue(should_align_preferred_workspace(WORKSPACE_NAME, MANAGER_WORKSPACE_NAME))
        self.assertFalse(should_align_preferred_workspace(MANAGER_WORKSPACE_NAME, MANAGER_WORKSPACE_NAME))
        self.assertFalse(should_align_preferred_workspace("自定义工作台", MANAGER_WORKSPACE_NAME))

    def test_resets_standard_default_apps(self):
        self.assertTrue(should_reset_default_app(None))
        self.assertTrue(should_reset_default_app("frappe"))
        self.assertTrue(should_reset_default_app("hrms"))
        self.assertFalse(should_reset_default_app("aihr"))

    def test_resets_english_language_defaults(self):
        self.assertTrue(should_reset_language(None))
        self.assertTrue(should_reset_language("en"))
        self.assertFalse(should_reset_language("zh"))

    def test_prefers_workspace_by_role(self):
        self.assertEqual(
            preferred_workspace_for_roles([AIHR_HIRING_MANAGER_ROLE]),
            MANAGER_WORKSPACE_NAME,
        )
        self.assertEqual(
            preferred_workspace_for_roles([INTERVIEWER_ROLE]),
            INTERVIEWER_WORKSPACE_NAME,
        )
        self.assertEqual(
            preferred_workspace_for_roles([HR_USER_ROLE]),
            WORKSPACE_NAME,
        )
        self.assertEqual(
            preferred_workspace_for_roles([HR_MANAGER_ROLE, AIHR_HIRING_MANAGER_ROLE]),
            WORKSPACE_NAME,
        )


if __name__ == "__main__":
    unittest.main()
