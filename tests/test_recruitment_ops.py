import unittest

from aihr.services.recruitment_ops import (
    build_requisition_payload,
    generate_requisition_agency_brief,
    get_screening_next_action,
)


class RecruitmentOpsTests(unittest.TestCase):
    def test_builds_requisition_payload_from_custom_fields(self):
        payload = build_requisition_payload(
            {
                "designation": "HRBP",
                "department": "People",
                "aihr_work_city": "Shanghai",
                "aihr_work_mode": "Hybrid",
                "aihr_work_schedule": "周一至周五 10:00-19:00",
                "aihr_salary_currency": "CNY",
                "aihr_salary_min": 25000,
                "aihr_salary_max": 35000,
                "aihr_must_have_skills": "recruiting, onboarding",
                "aihr_nice_to_have_skills": "communication",
                "reason_for_requesting": "支持招聘主链路联调",
            }
        )

        self.assertEqual(payload["designation"], "HRBP")
        self.assertEqual(payload["work_city"], "Shanghai")
        self.assertEqual(payload["salary_currency"], "CNY")
        self.assertEqual(payload["must_have_skills"], "recruiting, onboarding")

    def test_generates_agency_brief_from_requisition_payload(self):
        brief = generate_requisition_agency_brief(
            {
                "designation": "HRBP",
                "department": "People",
                "aihr_work_city": "Shanghai",
                "aihr_work_mode": "Hybrid",
                "aihr_salary_currency": "CNY",
                "aihr_salary_min": "25000",
                "aihr_salary_max": "35000",
                "aihr_must_have_skills": "recruiting, onboarding",
            }
        )

        self.assertIn("岗位名称：HRBP", brief)
        self.assertIn("工作城市：Shanghai", brief)
        self.assertIn("CNY 25000 - 35000", brief)

    def test_maps_screening_status_to_next_action(self):
        self.assertEqual(get_screening_next_action("Advance"), "安排经理初筛")
        self.assertEqual(get_screening_next_action("Ready for Review"), "经理复核候选人摘要")
        self.assertEqual(get_screening_next_action("Hold"), "补充信息或暂缓推进")


if __name__ == "__main__":
    unittest.main()
