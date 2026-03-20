import unittest

from aihr.services.resume_parser import parse_resume_text


class ResumeParserTests(unittest.TestCase):
    def test_extracts_basic_fields(self):
        resume_text = """
        Jane Smith
        jane@demo.com
        +86 138-0013-8000
        Location: Shanghai
        6 years of experience in recruiting, onboarding, payroll, and excel.
        """

        result = parse_resume_text(resume_text)

        self.assertEqual(result["name"], "Jane Smith")
        self.assertEqual(result["city"], "Shanghai")
        self.assertEqual(result["years_of_experience"], 6)
        self.assertIn("jane@demo.com", result["emails"])
        self.assertIn("recruiting", result["skills"])
        self.assertIn("excel", result["skills"])


if __name__ == "__main__":
    unittest.main()

