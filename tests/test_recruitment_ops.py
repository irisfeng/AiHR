import unittest

from aihr.services.recruitment_ops import (
    build_feedback_summary,
    build_requisition_payload,
    build_interviewer_pack,
    build_onboarding_summary,
    build_offer_handoff_notes,
    default_onboarding_activities,
    generate_requisition_agency_brief,
    get_feedback_next_action,
    get_interview_follow_up_action,
    get_onboarding_next_action,
    get_offer_next_action,
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

    def test_builds_interviewer_pack(self):
        pack = build_interviewer_pack(
            candidate_name="张敏",
            opening_title="HRBP - AIHR MVP Demo",
            interview_round="AIHR 首轮面试",
            interview_mode="视频",
            schedule_label="2026-03-21 14:00 - 15:00",
            ai_summary="AI 启发式匹配分 86，候选人具备招聘和薪酬经验。",
            strengths=["招聘协同经验完整", "对入职与薪酬交接敏感"],
            risks=["尚未确认到岗时间"],
            suggested_questions=["请分享你推进 Offer 到入职的典型案例"],
        )

        self.assertIn("AIHR 面试官资料包", pack)
        self.assertIn("张敏", pack)
        self.assertIn("招聘协同经验完整", pack)
        self.assertIn("请分享你推进 Offer 到入职的典型案例", pack)

    def test_maps_interview_follow_up_action(self):
        action = get_interview_follow_up_action("Under Review", "2026-03-22 12:00:00")

        self.assertIn("催收面试反馈", action)
        self.assertIn("2026-03-22", action)

    def test_builds_offer_handoff_notes(self):
        notes = build_offer_handoff_notes(
            candidate_name="Mia Zhang",
            opening_title="HRBP - AIHR MVP Demo",
            offer_status="Accepted",
            onboarding_owner="manager.demo@aihr.local",
            payroll_handoff_status="Ready",
            salary_expectation="CNY 28000 - 32000",
            compensation_notes="建议确认试用期薪资和补贴项。",
        )

        self.assertIn("AIHR Offer 交接摘要", notes)
        self.assertIn("Mia Zhang", notes)
        self.assertIn("建议确认试用期薪资和补贴项。", notes)
        self.assertIn("发起入职任务", notes)

    def test_maps_offer_next_action(self):
        self.assertEqual(get_offer_next_action("Awaiting Response", "Not Started"), "跟进候选人反馈并确认到岗时间")
        self.assertEqual(get_offer_next_action("Accepted", "Ready"), "发起入职任务并通知薪资建档负责人")

    def test_maps_feedback_next_action(self):
        self.assertEqual(get_feedback_next_action("Cleared"), "同步面试结论并推进 Offer 评估")
        self.assertEqual(get_feedback_next_action("Rejected"), "同步淘汰结论并归档面试反馈")

    def test_builds_feedback_summary(self):
        summary = build_feedback_summary(
            interviewer="manager.demo@aihr.local",
            result="Cleared",
            average_rating="4.3 / 5",
            feedback="候选人沟通顺畅，流程意识强。",
            ratings=["招聘协同: 4 / 5", "业务沟通: 5 / 5"],
        )

        self.assertIn("AIHR 面试反馈摘要", summary)
        self.assertIn("manager.demo@aihr.local", summary)
        self.assertIn("候选人沟通顺畅", summary)

    def test_builds_default_onboarding_activities(self):
        activities = default_onboarding_activities("manager.demo@aihr.local")

        self.assertEqual(len(activities), 4)
        self.assertEqual(activities[0]["activity_name"], "确认 Offer 与入职日期")
        self.assertEqual(activities[1]["user"], "manager.demo@aihr.local")

    def test_builds_onboarding_summary(self):
        summary = build_onboarding_summary(
            candidate_name="Mia Zhang",
            opening_title="HRBP - AIHR MVP Demo",
            handoff_owner="manager.demo@aihr.local",
            boarding_status="In Process",
            payroll_ready=True,
            date_of_joining="2026-04-04",
            activities=["确认 Offer 与入职日期", "同步薪酬建档信息"],
            preboarding_notes="请确认身份证明、学历材料和银行卡信息。",
        )

        self.assertIn("AIHR 入职交接摘要", summary)
        self.assertIn("Mia Zhang", summary)
        self.assertIn("同步薪酬建档信息", summary)

    def test_maps_onboarding_next_action(self):
        self.assertEqual(get_onboarding_next_action("Pending", False), "先补齐预入职资料和薪酬建档信息")
        self.assertEqual(get_onboarding_next_action("In Process", True), "推进入职活动并创建员工档案")
        self.assertEqual(get_onboarding_next_action("Completed", True), "确认员工档案与首月薪资信息")


if __name__ == "__main__":
    unittest.main()
