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
        overview = self.client.get("/api/overview")

        self.assertEqual(candidates.status_code, 200)
        self.assertEqual(jobs.status_code, 200)
        self.assertEqual(interviews.status_code, 200)
        self.assertEqual(overview.status_code, 200)
        self.assertEqual(len(candidates.json()), 5)
        self.assertEqual(len(jobs.json()), 4)
        self.assertEqual(len(interviews.json()), 4)
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


if __name__ == "__main__":
    unittest.main()
