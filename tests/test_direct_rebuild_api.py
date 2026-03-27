import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.app import main, store


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


if __name__ == "__main__":
    unittest.main()
