import unittest

from aihr.services.screening import build_agency_brief, screen_candidate


class ScreeningTests(unittest.TestCase):
    def test_candidate_screening_scores_overlap(self):
        parsed_resume = {
            "name": "Jane Smith",
            "emails": ["jane@demo.com"],
            "phones": ["13800138000"],
            "city": "Shanghai",
            "years_of_experience": 6,
            "skills": ["recruiting", "onboarding", "payroll", "excel"],
        }

        result = screen_candidate(
            parsed_resume=parsed_resume,
            job_requirements="Need 5 years recruiting, onboarding, payroll, and excel experience in Shanghai.",
            preferred_skills="employee relations",
            preferred_city="Shanghai",
        )

        self.assertGreaterEqual(result["overall_score"], 70)
        self.assertEqual(result["recommended_status"], "Advance")
        self.assertIn("recruiting", result["matched_skills"])
        self.assertIn("AI 启发式匹配分", result["summary"])
        self.assertTrue(any("核心技能匹配度较高" in item for item in result["strengths"]))

    def test_agency_brief_generation(self):
        brief = build_agency_brief(
            {
                "job_title": "HRBP",
                "department": "People",
                "work_city": "Shanghai",
                "work_mode": "Hybrid",
                "salary_currency": "CNY",
                "salary_min": "25000",
                "salary_max": "35000",
                "must_have_skills": "recruiting, onboarding",
            }
        )

        self.assertIn("岗位名称：HRBP", brief)
        self.assertIn("Shanghai", brief)
        self.assertIn("CNY 25000 - 35000", brief)
        self.assertIn("代理说明", brief)

    def test_chinese_requirement_sentences_are_not_treated_as_skills(self):
        result = screen_candidate(
            parsed_resume={
                "name": "张敏",
                "emails": ["zhangmin@demo.com"],
                "phones": ["13800138001"],
                "city": "上海",
                "years_of_experience": 5,
                "skills": ["招聘", "入职", "薪酬", "员工关系"],
            },
            job_requirements="负责招聘、入职、组织协同，支持 AIHR 系统试运行。需要 5 年经验。",
            preferred_skills="沟通",
            preferred_city="上海",
        )

        self.assertIn("组织协同", result["missing_skills"])
        self.assertNotIn("负责招聘、入职、组织协同，支持 aihr 系统试运行。", result["missing_skills"])

    def test_chinese_resume_can_reach_advance_with_matching_profile(self):
        result = screen_candidate(
            parsed_resume={
                "name": "王小雨",
                "emails": ["wangxiaoyu@demo.com"],
                "phones": ["13800138011"],
                "city": "上海",
                "years_of_experience": 6,
                "skills": ["招聘", "面试", "入职", "数据分析"],
            },
            job_requirements=(
                "负责中文招聘需求梳理、简历初筛、面试协同与候选人推进。"
                "优先考虑具备招聘、面试、入职和数据分析经验的候选人。需要 4 年以上相关经验。"
            ),
            preferred_skills="薪酬, 员工关系, 沟通",
            preferred_city="上海",
        )

        self.assertGreaterEqual(result["overall_score"], 80)
        self.assertEqual(result["recommended_status"], "Advance")
        self.assertIn("招聘", result["matched_skills"])
        self.assertIn("面试", result["matched_skills"])
        self.assertIn("AI 启发式匹配分", result["summary"])
        self.assertTrue(any("上海" in item for item in result["strengths"]))


if __name__ == "__main__":
    unittest.main()
