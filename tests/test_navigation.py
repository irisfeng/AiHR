import unittest

from aihr.setup.navigation import (
    normalize_route_history_route,
    normalize_workspace_label,
    sanitize_frequently_visited_links,
    should_hide_frequent_link,
    should_hide_route_history,
)


class NavigationHistoryTests(unittest.TestCase):
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
