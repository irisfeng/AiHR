import unittest
from types import SimpleNamespace
from unittest.mock import patch

from aihr.setup.navigation import (
    AIHR_DESK_HOME,
    _redirect_if_unauthorized_doc_route,
    get_preferred_desk_home,
    is_probably_logged_in_system_user,
    normalize_desk_path,
    normalize_route_history_route,
    normalize_workspace_label,
    sanitize_frequently_visited_links,
    should_hide_frequent_link,
    should_hide_route_history,
)


class NavigationHistoryTests(unittest.TestCase):
    def test_logged_in_system_user_can_be_detected_from_user_or_cookies(self):
        self.assertTrue(is_probably_logged_in_system_user("Administrator"))
        self.assertTrue(
            is_probably_logged_in_system_user(
                "Guest",
                {"system_user": "yes", "user_id": "Administrator"},
            )
        )
        self.assertFalse(
            is_probably_logged_in_system_user(
                "Guest",
                {"system_user": "no", "user_id": "Guest"},
            )
        )

    def test_app_root_and_legacy_workspace_paths_redirect_to_stable_routes(self):
        self.assertEqual(normalize_desk_path("/", "Administrator"), AIHR_DESK_HOME)
        self.assertEqual(normalize_desk_path("/app"), AIHR_DESK_HOME)
        self.assertEqual(normalize_desk_path("/me"), AIHR_DESK_HOME)
        self.assertEqual(normalize_desk_path("/app/user-profile", "Administrator"), AIHR_DESK_HOME)
        self.assertEqual(normalize_desk_path("/app/user-profile/Administrator", "Administrator"), AIHR_DESK_HOME)
        self.assertEqual(normalize_desk_path("/app/leaderboard/User", "Administrator"), AIHR_DESK_HOME)
        self.assertEqual(normalize_desk_path("/app/aihr-招聘总览"), AIHR_DESK_HOME)
        self.assertEqual(normalize_desk_path("/app/aihr-用人经理中心"), "/app/aihr-manager-review")
        self.assertEqual(normalize_desk_path("/", "Guest"), "/")

    def test_manager_like_roles_redirect_to_manager_workspace(self):
        roles = ["AIHR Hiring Manager", "Employee"]
        self.assertEqual(get_preferred_desk_home("delivery.manager@aihr.local", roles), "/app/aihr-manager-review")
        self.assertEqual(normalize_desk_path("/app", "delivery.manager@aihr.local", roles), "/app/aihr-manager-review")
        self.assertEqual(
            normalize_desk_path("/app/aihr-hiring-hq", "delivery.manager@aihr.local", roles),
            "/app/aihr-manager-review",
        )

    def test_hr_roles_keep_hr_workspace_as_default_home(self):
        roles = ["HR User", "HR Manager", "Employee"]
        self.assertEqual(get_preferred_desk_home("hr.demo@aihr.local", roles), "/app/aihr-hiring-hq")
        self.assertEqual(normalize_desk_path("/app", "hr.demo@aihr.local", roles), "/app/aihr-hiring-hq")

    def test_unauthorized_manager_doc_route_redirects_back_to_manager_home(self):
        fake_db = SimpleNamespace(exists=lambda doctype, name: doctype == "AI Screening" and name == "AI-SCR-00025")
        fake_frappe = SimpleNamespace(
            db=fake_db,
            has_permission=lambda *args, **kwargs: False,
            get_roles=lambda user: ["AIHR Hiring Manager", "Employee"],
        )
        fake_permissions = SimpleNamespace(_is_scoped_hiring_manager=lambda user: True)

        with patch.dict(
            "sys.modules",
            {
                "frappe": fake_frappe,
                "aihr.permissions": fake_permissions,
            },
        ):
            self.assertEqual(
                _redirect_if_unauthorized_doc_route("/app/ai-screening/AI-SCR-00025", "delivery.manager@aihr.local"),
                "/app/aihr-manager-review",
            )

    def test_authorized_manager_doc_route_is_not_redirected(self):
        fake_db = SimpleNamespace(exists=lambda doctype, name: doctype == "AI Screening" and name == "AI-SCR-00028")
        fake_frappe = SimpleNamespace(
            db=fake_db,
            has_permission=lambda *args, **kwargs: True,
            get_roles=lambda user: ["AIHR Hiring Manager", "Employee"],
        )
        fake_permissions = SimpleNamespace(_is_scoped_hiring_manager=lambda user: True)

        with patch.dict(
            "sys.modules",
            {
                "frappe": fake_frappe,
                "aihr.permissions": fake_permissions,
            },
        ):
            self.assertIsNone(
                _redirect_if_unauthorized_doc_route("/app/ai-screening/AI-SCR-00028", "delivery.manager@aihr.local")
            )

    def test_legacy_workspace_labels_are_normalized(self):
        self.assertEqual(normalize_workspace_label("AIHR 招聘作战台"), "AIHR 招聘总览")
        self.assertEqual(normalize_workspace_label("AIHR 用人经理台"), "AIHR 用人经理中心")
        self.assertEqual(normalize_workspace_label("AIHR 面试官台"), "AIHR 面试协同中心")

    def test_legacy_route_history_is_rewritten(self):
        self.assertEqual(
            normalize_route_history_route("Workspaces/AIHR 招聘作战台"),
            "Workspaces/AIHR 招聘总览",
        )
        self.assertEqual(
            normalize_route_history_route("Workspaces/AIHR 面试官台"),
            "Workspaces/AIHR 面试协同中心",
        )

    def test_generic_hr_workspace_history_is_hidden(self):
        self.assertTrue(should_hide_route_history("Workspaces/HR"))
        self.assertFalse(should_hide_route_history("Workspaces/AIHR 招聘总览"))

    def test_aihr_workspace_frequent_links_are_hidden(self):
        self.assertTrue(should_hide_frequent_link("Workspaces/AIHR 招聘总览"))
        self.assertTrue(should_hide_frequent_link("Workspaces/HR"))
        self.assertTrue(should_hide_frequent_link("Workspaces/Home"))
        self.assertFalse(should_hide_frequent_link("List/Job Requisition/List"))

    def test_frequent_links_drop_hidden_entries_and_dedupe(self):
        links = [
            {"route": "Workspaces/AIHR 招聘作战台", "count": 5},
            {"route": "Workspaces/AIHR 招聘总览", "count": 3},
            {"route": "Workspaces/HR", "count": 9},
            {"route": "List/Job Requisition/List", "count": 2},
        ]

        self.assertEqual(
            sanitize_frequently_visited_links(links),
            [
                {"route": "List/Job Requisition/List", "count": 2},
            ],
        )


if __name__ == "__main__":
    unittest.main()
