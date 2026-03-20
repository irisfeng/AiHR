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

    def test_extracts_chinese_resume_fields(self):
        resume_text = """
        张敏
        zhangmin@demo.com
        13800138001
        现居：上海
        5年招聘、入职、薪酬和员工关系经验，熟悉 Excel 与数据分析。
        """

        result = parse_resume_text(resume_text)

        self.assertEqual(result["name"], "张敏")
        self.assertEqual(result["city"], "上海")
        self.assertEqual(result["years_of_experience"], 5)
        self.assertIn("招聘", result["skills"])
        self.assertIn("入职", result["skills"])
        self.assertIn("薪酬", result["skills"])
        self.assertIn("员工关系", result["skills"])


if __name__ == "__main__":
    unittest.main()
