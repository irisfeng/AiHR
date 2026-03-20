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

        self.assertIn("Role: HRBP", brief)
        self.assertIn("Shanghai", brief)
        self.assertIn("CNY 25000 - 35000", brief)


if __name__ == "__main__":
    unittest.main()
