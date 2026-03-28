import io
import tempfile
import time
import unittest
from pathlib import Path
from zipfile import ZipFile

from fastapi.testclient import TestClient

from apps.api.app import main, store


DOCX_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>张三</w:t></w:r></w:p>
    <w:p><w:r><w:t>现居上海</w:t></w:r></w:p>
    <w:p><w:r><w:t>6年 Python、FastAPI、PostgreSQL 经验。</w:t></w:r></w:p>
    <w:p><w:r><w:t>zhangsan@example.com</w:t></w:r></w:p>
  </w:body>
</w:document>
"""


class DirectRebuildApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "aihr-test.sqlite3"
        store.set_database_path(self.database_path)
        store.bootstrap_database()
        self.client = TestClient(main.app)

    def tearDown(self):
        self.client.close()
        store.set_database_path(None)
        self.temp_dir.cleanup()

    def test_seeded_endpoints_bootstrap_records(self):
        candidates = self.client.get("/api/candidates")
        jobs = self.client.get("/api/jobs")
        interviews = self.client.get("/api/interviews")
        offers = self.client.get("/api/offers")
        overview = self.client.get("/api/overview")

        self.assertEqual(candidates.status_code, 200)
        self.assertEqual(jobs.status_code, 200)
        self.assertEqual(interviews.status_code, 200)
        self.assertEqual(offers.status_code, 200)
        self.assertEqual(overview.status_code, 200)
        self.assertEqual(len(candidates.json()), 5)
        self.assertEqual(len(jobs.json()), 4)
        self.assertEqual(len(interviews.json()), 4)
        self.assertEqual(len(offers.json()), 2)
        self.assertEqual(overview.json()["title"], "AIHR Recruiting OS")

    def test_work_queue_groups_items_by_hr_action(self):
        response = self.client.get("/api/work-queue")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["groups"][0]["key"], "requisition_intake")
        self.assertEqual(payload["groups"][0]["title"], "待整理需求")
        self.assertGreaterEqual(payload["groups"][0]["count"], 1)
        self.assertIn("title", payload["groups"][0]["items"][0])
        self.assertIn("nextAction", payload["groups"][0]["items"][0])

    def test_create_requisition_intake_extracts_missing_fields_and_creates_draft(self):
        response = self.client.post(
            "/api/requisition-intakes",
            json={
                "owner": "周岩",
                "hiring_manager": "张经理",
                "raw_request_text": "想招一个资深后端，偏 Python 和微服务，最好尽快到岗。",
            },
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["owner"], "周岩")
        self.assertEqual(payload["hiringManager"], "张经理")
        self.assertEqual(payload["status"], "待确认 JD")
        self.assertIn("Python", " ".join(payload["extractedPayload"].values()))
        self.assertIn("地点缺失", payload["missingFields"])
        self.assertEqual(payload["jdText"], "")

    def test_create_candidate_persists_to_subsequent_reads(self):
        created = self.client.post(
            "/api/candidates",
            json={
                "name": "夜班候选人",
                "role": "资深后端工程师",
                "city": "上海",
                "experience": "6 年",
                "owner": "周岩",
                "source": "手动录入",
                "score": 88,
                "skills": ["Python", "FastAPI"],
            },
        )

        self.assertEqual(created.status_code, 201)
        payload = created.json()
        self.assertEqual(payload["name"], "夜班候选人")

        candidates = self.client.get("/api/candidates").json()
        self.assertTrue(any(item["name"] == "夜班候选人" for item in candidates))

    def test_create_candidate_exposes_initial_timeline_event(self):
        created = self.client.post(
            "/api/candidates",
            json={
                "name": "林起",
                "role": "资深后端工程师",
                "city": "上海",
                "experience": "5 年",
                "owner": "周岩",
                "source": "内推",
                "score": 82,
                "skills": ["Python", "PostgreSQL"],
            },
        )

        self.assertEqual(created.status_code, 201)
        candidate_id = created.json()["id"]

        timeline = self.client.get(f"/api/candidates/{candidate_id}/timeline")
        self.assertEqual(timeline.status_code, 200)
        self.assertEqual(len(timeline.json()), 1)
        self.assertEqual(timeline.json()[0]["title"], "候选人已录入")
        self.assertIn("内推", timeline.json()[0]["detail"])

    def test_create_job_and_interview_updates_job_interview_count(self):
        created_job = self.client.post(
            "/api/jobs",
            json={
                "title": "平台 SRE 负责人",
                "team": "基础架构",
                "location": "上海",
                "mode": "Hybrid",
                "headcount": 1,
                "owner": "顾峰",
                "urgency": "critical",
                "summary": "负责平台稳定性与事故响应。",
                "skills": ["SRE", "Kubernetes"],
            },
        )
        self.assertEqual(created_job.status_code, 201)

        created_interview = self.client.post(
            "/api/interviews",
            json={
                "candidate_name": "沈知越",
                "role": "平台 SRE 负责人",
                "round": "技术一面",
                "mode": "视频",
                "time_label": "03-30 11:00",
                "interviewer": "顾峰",
                "summary": "重点问事故复盘、值班和变更治理。",
            },
        )
        self.assertEqual(created_interview.status_code, 201)
        self.assertEqual(created_interview.json()["candidateName"], "沈知越")

        jobs = self.client.get("/api/jobs").json()
        sre_job = next(item for item in jobs if item["title"] == "平台 SRE 负责人")
        self.assertEqual(sre_job["interviews"], 1)

    def test_manager_review_can_schedule_interview_from_candidate_queue(self):
        reviewed = self.client.post(
            "/api/candidates/cand-005/review",
            json={
                "decision": "advance",
                "summary": "核心后端经验匹配，先进入技术一面。",
                "actor": "周岩",
                "next_step": "安排技术一面",
                "schedule_interview": True,
                "interview_round": "技术一面",
                "interview_time": "03-30 15:00",
                "interviewer": "顾峰",
                "interview_mode": "视频",
            },
        )

        self.assertEqual(reviewed.status_code, 200)
        payload = reviewed.json()
        self.assertEqual(payload["candidate"]["status"], "面试中")
        self.assertEqual(payload["candidate"]["nextAction"], "等待技术一面反馈")
        self.assertEqual(payload["interview"]["candidateName"], "周闻笙")
        self.assertEqual(payload["interview"]["round"], "技术一面")
        self.assertEqual(payload["interview"]["interviewer"], "顾峰")

        jobs = self.client.get("/api/jobs").json()
        backend_job = next(item for item in jobs if item["id"] == "job-backend-01")
        self.assertEqual(backend_job["interviews"], 7)

        timeline = self.client.get("/api/candidates/cand-005/timeline").json()
        titles = {item["title"] for item in timeline}
        self.assertIn("经理复核：通过", titles)
        self.assertIn("已安排技术一面", titles)

    def test_manager_review_can_hold_candidate_without_creating_interview(self):
        reviewed = self.client.post(
            "/api/candidates/cand-002/review",
            json={
                "decision": "hold",
                "summary": "需要补问多模型编排案例，再决定是否进入下一轮。",
                "actor": "沈珂",
                "next_step": "补充多模型编排案例",
            },
        )

        self.assertEqual(reviewed.status_code, 200)
        payload = reviewed.json()
        self.assertEqual(payload["candidate"]["status"], "待补充信息")
        self.assertEqual(payload["candidate"]["nextAction"], "补充多模型编排案例")
        self.assertIsNone(payload["interview"])

        interviews = self.client.get("/api/interviews").json()
        self.assertEqual(len(interviews), 4)

        timeline = self.client.get("/api/candidates/cand-002/timeline").json()
        self.assertEqual(timeline[0]["title"], "经理复核：补充信息")
        self.assertIn("补充多模型编排案例", timeline[0]["detail"])

    def test_submit_interview_feedback_updates_candidate_and_timeline(self):
        applied = self.client.post(
            "/api/interviews/int-002/feedback",
            json={
                "decision": "通过",
                "summary": "模型服务工程化比较扎实，建议进入终面。",
                "strengths": ["能讲清 GPU 成本优化", "熟悉推理服务上线流程"],
                "concerns": ["多模型编排案例还需要补问"],
                "next_step": "安排终面",
                "actor": "沈珂",
            },
        )

        self.assertEqual(applied.status_code, 200)
        payload = applied.json()
        self.assertEqual(payload["interview"]["status"], "已通过")
        self.assertEqual(payload["candidate"]["status"], "建议推进")
        self.assertEqual(payload["candidate"]["nextAction"], "安排终面")

        interviews = self.client.get("/api/interviews").json()
        updated_interview = next(item for item in interviews if item["id"] == "int-002")
        self.assertEqual(updated_interview["status"], "已通过")
        self.assertIn("模型服务工程化比较扎实", updated_interview["summary"])

        candidates = self.client.get("/api/candidates").json()
        updated_candidate = next(item for item in candidates if item["id"] == "cand-002")
        self.assertEqual(updated_candidate["status"], "建议推进")
        self.assertEqual(updated_candidate["nextAction"], "安排终面")

        timeline = self.client.get("/api/candidates/cand-002/timeline")
        self.assertEqual(timeline.status_code, 200)
        self.assertGreaterEqual(len(timeline.json()), 1)
        self.assertEqual(timeline.json()[0]["title"], "业务面反馈：通过")
        self.assertIn("模型服务工程化比较扎实", timeline.json()[0]["detail"])
        self.assertEqual(timeline.json()[0]["actor"], "沈珂")

    def test_create_offer_handoff_updates_job_candidate_and_timeline(self):
        created = self.client.post(
            "/api/offers",
            json={
                "candidate_id": "cand-001",
                "job_id": "job-backend-01",
                "status": "Accepted",
                "salary_expectation": "45k x 15",
                "compensation_notes": "确认试用期 3 个月，补贴口径与签字链路。",
                "onboarding_owner": "周岩",
                "payroll_owner": "林薇",
            },
        )

        self.assertEqual(created.status_code, 201)
        payload = created.json()
        self.assertEqual(payload["candidateName"], "王书衡")
        self.assertEqual(payload["payrollHandoffStatus"], "Not Started")
        self.assertEqual(payload["nextAction"], "补齐入职资料并准备薪酬交接")
        self.assertIn("AIHR Offer 交接摘要", payload["handoffSummary"])

        offers = self.client.get("/api/offers").json()
        created_offer = next(item for item in offers if item["id"] == payload["id"])
        self.assertEqual(created_offer["payrollOwner"], "林薇")

        jobs = self.client.get("/api/jobs").json()
        backend_job = next(item for item in jobs if item["id"] == "job-backend-01")
        self.assertEqual(backend_job["offers"], 2)

        candidates = self.client.get("/api/candidates").json()
        candidate = next(item for item in candidates if item["id"] == "cand-001")
        self.assertEqual(candidate["status"], "Offer 已接受")
        self.assertEqual(candidate["nextAction"], "补齐入职资料并准备薪酬交接")

        timeline = self.client.get("/api/candidates/cand-001/timeline").json()
        self.assertEqual(timeline[0]["title"], "Offer 交接已创建")
        self.assertIn("45k x 15", timeline[0]["detail"])

    def test_mark_offer_payroll_ready_updates_offer_and_candidate_next_action(self):
        created = self.client.post(
            "/api/offers",
            json={
                "candidate_id": "cand-003",
                "job_id": "job-recruiting-01",
                "status": "Accepted",
                "salary_expectation": "28k x 14",
                "compensation_notes": "确认到岗日期和首月发薪规则。",
                "onboarding_owner": "刘颖",
                "payroll_owner": "陈琳",
            },
        )
        self.assertEqual(created.status_code, 201)
        offer_id = created.json()["id"]

        updated = self.client.post(f"/api/offers/{offer_id}/payroll-ready")
        self.assertEqual(updated.status_code, 200)
        payload = updated.json()
        self.assertEqual(payload["offer"]["payrollHandoffStatus"], "Ready")
        self.assertEqual(payload["offer"]["nextAction"], "发起入职任务并通知薪资建档负责人")
        self.assertIn("AIHR 薪酬交接摘要", payload["offer"]["payrollHandoffSummary"])

        candidates = self.client.get("/api/candidates").json()
        candidate = next(item for item in candidates if item["id"] == "cand-003")
        self.assertEqual(candidate["nextAction"], "发起入职任务并通知薪资建档负责人")

        timeline = self.client.get("/api/candidates/cand-003/timeline").json()
        self.assertEqual(timeline[0]["title"], "薪酬交接已就绪")
        self.assertEqual(timeline[0]["actor"], "陈琳")

    def test_resume_intake_job_parses_zip_and_creates_candidates(self):
        response = self.client.post(
            "/api/intake-jobs",
            files={"archive": ("bundle.zip", self._build_resume_bundle(), "application/zip")},
            data={
                "job_id": "job-backend-01",
                "owner": "周岩",
                "source": "ZIP 简历包",
            },
        )
        self.assertEqual(response.status_code, 202)

        job_id = response.json()["id"]
        job_payload = self._wait_for_intake_job(job_id)
        self.assertEqual(job_payload["status"], "Completed")
        self.assertEqual(job_payload["summary"]["parsedCount"], 2)
        self.assertEqual(job_payload["summary"]["unsupportedCount"], 1)
        self.assertEqual(job_payload["summary"]["createdCandidateCount"], 2)

        parsed_items = [item for item in job_payload["items"] if item["status"] == "Parsed"]
        self.assertEqual(len(parsed_items), 2)
        self.assertTrue(all(item["candidateId"] for item in parsed_items))

        candidates = self.client.get("/api/candidates").json()
        created_names = {item["name"] for item in candidates}
        self.assertIn("张三", created_names)
        self.assertIn("李四", created_names)

        jobs = self.client.get("/api/jobs").json()
        backend_job = next(item for item in jobs if item["id"] == "job-backend-01")
        self.assertEqual(backend_job["applicants"], 38)
        self.assertEqual(backend_job["screened"], 17)

    def test_resume_intake_job_detail_lists_created_candidates(self):
        created = self.client.post(
            "/api/intake-jobs",
            files={"archive": ("bundle.zip", self._build_resume_bundle(), "application/zip")},
            data={
                "job_id": "job-backend-01",
                "owner": "周岩",
                "source": "ZIP 简历包",
            },
        )
        self.assertEqual(created.status_code, 202)

        job_id = created.json()["id"]
        job_payload = self._wait_for_intake_job(job_id)
        parsed_item = next(item for item in job_payload["items"] if item["fileName"] == "resume.docx")
        self.assertEqual(parsed_item["parserEngine"], "DOCX")
        self.assertEqual(parsed_item["parsedResume"]["name"], "张三")
        self.assertTrue(parsed_item["candidateId"])
        self.assertEqual(parsed_item["candidateSummary"]["name"], "张三")
        self.assertIn(parsed_item["candidateSummary"]["status"], {"建议推进", "待经理复核", "建议暂缓"})
        self.assertIsInstance(parsed_item["candidateSummary"]["score"], int)
        self.assertTrue(parsed_item["candidateSummary"]["nextAction"])
        self.assertTrue(parsed_item["candidateSummary"]["highlights"])
        self.assertTrue(parsed_item["candidateSummary"]["risks"])

    def _wait_for_intake_job(self, job_id: str) -> dict:
        deadline = time.time() + 5
        while time.time() < deadline:
            payload = self.client.get(f"/api/intake-jobs/{job_id}")
            self.assertEqual(payload.status_code, 200)
            body = payload.json()
            if body["status"] in {"Completed", "Failed"}:
                return body
            time.sleep(0.05)
        self.fail(f"Timed out waiting for intake job {job_id}")

    @staticmethod
    def _build_resume_bundle() -> bytes:
        buffer = io.BytesIO()
        with ZipFile(buffer, "w") as bundle:
            bundle.writestr("resume.docx", DirectRebuildApiTests._build_docx_bytes())
            bundle.writestr("resume.txt", "李四\n现居杭州\n4年 Python、Redis、PostgreSQL 经验\nlisi@example.com")
            bundle.writestr("notes.xlsx", b"binary")
        return buffer.getvalue()

    @staticmethod
    def _build_docx_bytes() -> bytes:
        buffer = io.BytesIO()
        with ZipFile(buffer, "w") as archive:
            archive.writestr("[Content_Types].xml", "")
            archive.writestr("word/document.xml", DOCX_XML)
        return buffer.getvalue()


if __name__ == "__main__":
    unittest.main()
