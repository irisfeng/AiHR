import os
import unittest
from unittest.mock import patch

from aihr.services import ai_assistant


class AIAssistantTests(unittest.TestCase):
    def test_enhance_screening_returns_heuristic_result_when_llm_disabled(self):
        heuristic = {
            "overall_score": 72,
            "recommended_status": "Ready for Review",
            "matched_skills": ["招聘", "面试"],
            "missing_skills": ["数据分析"],
            "summary": "AI 启发式匹配分为 72/100。",
            "strengths": ["候选人具备招聘经验。"],
            "risks": ["数据分析能力需确认。"],
            "suggested_questions": ["请说明你如何做招聘数据复盘。"],
        }

        with patch.dict(os.environ, {}, clear=True):
            result = ai_assistant.enhance_screening_with_llm(
                parsed_resume={"name": "张敏"},
                resume_text="张敏，6年招聘经验。",
                opening_title="招聘运营经理",
                job_requirements="需要招聘与面试经验。",
                preferred_skills="数据分析",
                preferred_city="上海",
                heuristic_screening=heuristic,
            )

        self.assertEqual(result["overall_score"], 72)
        self.assertEqual(result["recommended_status"], "Ready for Review")
        self.assertEqual(result["scoring_mode"], "heuristic")

    def test_enhance_screening_uses_llm_payload_when_available(self):
        heuristic = {
            "overall_score": 72,
            "recommended_status": "Ready for Review",
            "matched_skills": ["招聘"],
            "missing_skills": ["数据分析"],
            "summary": "AI 启发式匹配分为 72/100。",
            "strengths": ["候选人具备招聘经验。"],
            "risks": ["数据分析能力需确认。"],
            "suggested_questions": ["请说明你如何做招聘数据复盘。"],
        }

        with patch.dict(os.environ, {"AIHR_LLM_API_KEY": "demo"}, clear=True):
            with patch.object(
                ai_assistant,
                "_request_json_completion",
                return_value={
                    "overall_score": 88,
                    "recommended_status": "Advance",
                    "matched_skills": ["招聘", "面试", "入职"],
                    "missing_skills": ["薪酬"],
                    "summary": "候选人与岗位核心要求高度匹配，建议优先推进。",
                    "strengths": ["招聘推进经验扎实。", "面试协同经验完整。"],
                    "risks": ["薪酬协同经历待确认。"],
                    "suggested_questions": ["请分享你跨部门推进 Offer 的案例。"],
                },
            ):
                result = ai_assistant.enhance_screening_with_llm(
                    parsed_resume={"name": "张敏"},
                    resume_text="张敏，6年招聘经验。",
                    opening_title="招聘运营经理",
                    job_requirements="需要招聘与面试经验。",
                    preferred_skills="数据分析",
                    preferred_city="上海",
                    heuristic_screening=heuristic,
                )

        self.assertEqual(result["overall_score"], 88)
        self.assertEqual(result["recommended_status"], "Advance")
        self.assertEqual(result["scoring_mode"], "ai_semantic")
        self.assertIn("面试", result["matched_skills"])

    def test_build_interviewer_pack_returns_ai_result_when_available(self):
        with patch.dict(os.environ, {"AIHR_LLM_API_KEY": "demo"}, clear=True):
            with patch.object(ai_assistant, "_request_text_completion", return_value="AI 生成的面试资料包"):
                pack = ai_assistant.build_interviewer_pack_with_llm(
                    fallback_pack="fallback pack",
                    candidate_name="张敏",
                    opening_title="招聘运营经理",
                    interview_round="一面",
                    interview_mode="视频",
                    schedule_label="2026-03-22 15:00",
                    screening_summary="建议推进。",
                    strengths=["跨部门协同能力强"],
                    risks=["薪酬经验待确认"],
                    suggested_questions=["请说明招聘漏斗数据复盘方式"],
                )

        self.assertEqual(pack, "AI 生成的面试资料包")

    def test_feedback_summary_falls_back_when_llm_disabled(self):
        with patch.dict(os.environ, {}, clear=True):
            result = ai_assistant.summarize_interview_feedback_with_llm(
                candidate_name="张敏",
                opening_title="招聘运营经理",
                interview_round="一面",
                feedback_result="Cleared",
                feedback_text="候选人沟通清晰，推进意识强。",
                rating_rows=["沟通: 5 / 5"],
                screening_summary="建议推进",
                fallback_summary="AIHR 面试反馈摘要",
                default_next_action="推进 Offer 评估",
                default_hiring_recommendation="Yes",
            )

        self.assertEqual(result["summary"], "AIHR 面试反馈摘要")
        self.assertEqual(result["next_step_suggestion"], "推进 Offer 评估")
        self.assertEqual(result["hiring_recommendation"], "Yes")


if __name__ == "__main__":
    unittest.main()
