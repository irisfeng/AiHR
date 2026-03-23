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

    def test_fallback_resume_email_prefers_phone(self):
        value = recruitment._fallback_resume_email(
            file_name="买鑫实施运维工程师.pdf",
            applicant_name="买鑫",
            phone="15710031625",
            batch_reference="RIB-202603220001",
        )
        self.assertEqual(value, "resume-15710031625@aihr.local")

    def test_fallback_resume_email_generates_hash_when_phone_missing(self):
        value = recruitment._fallback_resume_email(
            file_name="曹杨宜简历.pdf",
            applicant_name="曹杨宜",
            phone="",
            batch_reference="RIB-202603220001",
        )
        self.assertTrue(value.startswith("resume-"))
        self.assertTrue(value.endswith("@aihr.local"))

    def test_build_resume_preview_payload_marks_pdf_as_embeddable(self):
        applicant = SimpleNamespace(
            resume_attachment="/private/files/交付工程师.pdf",
            aihr_resume_file_name="交付工程师.pdf",
        )
        payload = recruitment._build_resume_preview_payload(applicant, "这是候选人的中文简历正文")
        self.assertEqual(payload["kind"], "pdf")
        self.assertTrue(payload["can_embed"])
        self.assertEqual(payload["file_name"], "交付工程师.pdf")
        self.assertEqual(
            payload["preview_url"],
            "/api/method/download_file?file_url=%2Fprivate%2Ffiles%2F%E4%BA%A4%E4%BB%98%E5%B7%A5%E7%A8%8B%E5%B8%88.pdf",
        )

    def test_build_authorized_file_url_keeps_public_files_unchanged(self):
        self.assertEqual(recruitment._build_authorized_file_url("/files/demo.pdf"), "/files/demo.pdf")

    def test_parse_json_blob_returns_empty_dict_on_invalid_payload(self):
        self.assertEqual(recruitment._parse_json_blob("{bad-json"), {})

    def test_build_ai_screening_display_snapshots_prefers_readable_names(self):
        applicant = SimpleNamespace(
            name="APP-0001",
            applicant_name="陈寒",
            email_id="delivery.chenhan@aihr.local",
            job_title="HR-OPN-2026-0004",
        )
        opening = SimpleNamespace(job_title="交付工程师 - AIHR Demo")

        snapshots = recruitment._build_ai_screening_display_snapshots(applicant, opening)

        self.assertEqual(snapshots["candidate_name"], "陈寒")
        self.assertEqual(snapshots["opening_title"], "交付工程师 - AIHR Demo")


if __name__ == "__main__":
    unittest.main()
