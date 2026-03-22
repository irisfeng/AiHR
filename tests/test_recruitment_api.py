from types import SimpleNamespace
import unittest

from aihr.api import recruitment


class FakeDB:
    def get_value(self, doctype, name, fieldname):
        values = {
            "aihr_must_have_skills": "招聘, 面试, 入职, 数据分析",
            "aihr_nice_to_have_skills": "薪酬, 员工关系, 沟通",
        }
        return values.get(fieldname, "")


class FakeFrappe:
    def __init__(self):
        self.db = FakeDB()

    def get_doc(self, doctype, name):
        return SimpleNamespace(
            description="负责中文招聘需求梳理、简历初筛、面试协同与候选人推进。",
            job_requisition="REQ-0001",
        )


class RecruitmentApiTests(unittest.TestCase):
    def test_job_requirements_excludes_nice_to_have_skills(self):
        applicant = SimpleNamespace(job_title="HR-OPN-CN-0001")
        original_frappe = recruitment.frappe
        original_get_requisition_field = recruitment._get_requisition_field

        try:
            recruitment.frappe = FakeFrappe()
            recruitment._get_requisition_field = lambda applicant, fieldname: (
                "中文联调岗位：要求候选人能与业务部门高频沟通。"
                if fieldname == "description"
                else ""
            )
            requirements = recruitment._get_job_requirements(applicant)
        finally:
            recruitment.frappe = original_frappe
            recruitment._get_requisition_field = original_get_requisition_field

        self.assertIn("招聘, 面试, 入职, 数据分析", requirements)
        self.assertNotIn("薪酬, 员工关系, 沟通", requirements)


if __name__ == "__main__":
    unittest.main()
