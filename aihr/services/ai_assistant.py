from __future__ import annotations

import json
import os
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_LLM_BASE_URL = "https://api.openai.com/v1"
DEFAULT_LLM_MODEL = "gpt-5-mini"
DEFAULT_TIMEOUT_SECONDS = 60
ALLOWED_SCREENING_STATUSES = {"Advance", "Ready for Review", "Hold"}
ALLOWED_HIRING_RECOMMENDATIONS = {"Strong Yes", "Yes", "Maybe", "No"}


class AIAssistantError(RuntimeError):
    pass


def llm_is_enabled() -> bool:
    return bool(_get_api_key())


def enhance_screening_with_llm(
    *,
    parsed_resume: dict[str, Any],
    resume_text: str,
    opening_title: str,
    job_requirements: str,
    preferred_skills: str,
    preferred_city: str,
    heuristic_screening: dict[str, Any],
) -> dict[str, Any]:
    baseline = dict(heuristic_screening or {})
    baseline["scoring_mode"] = "heuristic"

    if not llm_is_enabled():
        return baseline

    prompt = (
        "请基于以下岗位需求和候选人简历，输出中文 JSON。"
        "你是资深招聘初筛助手，只能根据已提供信息判断，不能编造不存在的经历或技能。\n\n"
        f"岗位名称：{opening_title or '待定岗位'}\n"
        f"岗位要求：{job_requirements or '未提供'}\n"
        f"加分项：{preferred_skills or '无'}\n"
        f"工作城市：{preferred_city or '未限制'}\n\n"
        "候选人结构化信息：\n"
        f"{json.dumps(parsed_resume, ensure_ascii=False, indent=2)}\n\n"
        "候选人简历原文节选：\n"
        f"{_truncate_text(resume_text, 6000) or '未提取到原文。'}\n\n"
        "已有启发式基线结果（仅供参考，可覆盖）：\n"
        f"{json.dumps(heuristic_screening, ensure_ascii=False, indent=2)}\n\n"
        "请返回严格 JSON，字段如下：\n"
        "{"
        '"overall_score": 0,'
        '"recommended_status": "Advance | Ready for Review | Hold",'
        '"matched_skills": ["..."],'
        '"missing_skills": ["..."],'
        '"summary": "...",'
        '"strengths": ["..."],'
        '"risks": ["..."],'
        '"suggested_questions": ["..."]'
        "}\n"
        "要求：overall_score 为 0-100 整数；strengths/risks/suggested_questions 分别给 2-4 条；"
        "summary 不超过 150 字；输出必须是 JSON。"
    )

    try:
        payload = _request_json_completion(
            system_prompt=(
                "你是 AIHR 的中文招聘初筛助手。"
                "请做语义匹配和证据判断，优先考虑岗位硬性要求、项目深度、职责匹配度和信息可靠性。"
            ),
            user_prompt=prompt,
        )
    except AIAssistantError as exc:
        baseline["assistant_error"] = str(exc)
        return baseline

    normalized = _normalize_screening_payload(payload, baseline)
    normalized["scoring_mode"] = "ai_semantic"
    normalized["heuristic_baseline_score"] = baseline.get("overall_score", 0)
    return normalized


def build_interviewer_pack_with_llm(
    *,
    fallback_pack: str,
    candidate_name: str,
    opening_title: str,
    interview_round: str,
    interview_mode: str,
    schedule_label: str,
    screening_summary: str,
    strengths: list[str],
    risks: list[str],
    suggested_questions: list[str],
) -> str:
    if not llm_is_enabled():
        return fallback_pack

    prompt = (
        "请为面试官生成一份中文面试资料包，要求专业、克制、便于快速阅读。"
        "请使用纯文本，不要使用 Markdown 表格。"
        "结构请包含：候选人判断、建议重点追问、面试观察点、面后决策提示。\n\n"
        f"候选人：{candidate_name or '待补充'}\n"
        f"岗位：{opening_title or '待补充'}\n"
        f"轮次：{interview_round or '待补充'}\n"
        f"形式：{interview_mode or '待补充'}\n"
        f"时间：{schedule_label or '待安排'}\n\n"
        f"AI 初筛摘要：{screening_summary or '暂无'}\n"
        f"优势：{'; '.join(strengths) or '暂无'}\n"
        f"风险点：{'; '.join(risks) or '暂无'}\n"
        f"建议追问：{'; '.join(suggested_questions) or '暂无'}\n"
    )

    try:
        result = _request_text_completion(
            system_prompt=(
                "你是 AIHR 的中文面试助手。"
                "请把候选人摘要整理成一页内可读的面试资料包，帮助面试官快速抓重点。"
            ),
            user_prompt=prompt,
        )
    except AIAssistantError:
        return fallback_pack

    cleaned = result.strip()
    return cleaned or fallback_pack


def summarize_interview_feedback_with_llm(
    *,
    candidate_name: str,
    opening_title: str,
    interview_round: str,
    feedback_result: str,
    feedback_text: str,
    rating_rows: list[str],
    screening_summary: str,
    fallback_summary: str,
    default_next_action: str,
    default_hiring_recommendation: str,
) -> dict[str, str]:
    fallback = {
        "summary": fallback_summary,
        "interview_summary": _truncate_text(fallback_summary, 140),
        "next_step_suggestion": default_next_action,
        "hiring_recommendation": default_hiring_recommendation,
    }

    if not llm_is_enabled():
        return fallback

    prompt = (
        "请根据面试反馈生成中文 JSON。"
        "只根据提供的候选人摘要、评分项和面试官反馈进行判断，不要编造信息。\n\n"
        f"候选人：{candidate_name or '待补充'}\n"
        f"岗位：{opening_title or '待补充'}\n"
        f"轮次：{interview_round or '待补充'}\n"
        f"面试结论：{feedback_result or '待确认'}\n"
        f"候选人摘要：{screening_summary or '暂无'}\n"
        f"评分项：{'; '.join(rating_rows) or '暂无'}\n"
        f"面试官反馈：{feedback_text or '暂无'}\n\n"
        "请返回严格 JSON：\n"
        "{"
        '"summary": "...",'
        '"interview_summary": "...",'
        '"next_step_suggestion": "...",'
        '"hiring_recommendation": "Strong Yes | Yes | Maybe | No"'
        "}\n"
        "要求：summary 为完整中文总结；interview_summary 为 80 字内一句话；"
        "如果证据不足，hiring_recommendation 请选择 Maybe。"
    )

    try:
        payload = _request_json_completion(
            system_prompt=(
                "你是 AIHR 的中文面试决策助手。"
                "请根据面试反馈生成稳健的结论，优先指出证据和待确认项。"
            ),
            user_prompt=prompt,
        )
    except AIAssistantError as exc:
        fallback["assistant_error"] = str(exc)
        return fallback

    hiring_recommendation = str(payload.get("hiring_recommendation") or "").strip()
    if hiring_recommendation not in ALLOWED_HIRING_RECOMMENDATIONS:
        hiring_recommendation = default_hiring_recommendation

    summary = _sanitize_text(payload.get("summary"), fallback_summary)
    interview_summary = _sanitize_text(payload.get("interview_summary"), _truncate_text(summary, 140))
    next_step_suggestion = _sanitize_text(payload.get("next_step_suggestion"), default_next_action)

    return {
        "summary": summary,
        "interview_summary": _truncate_text(interview_summary, 140),
        "next_step_suggestion": next_step_suggestion,
        "hiring_recommendation": hiring_recommendation,
    }


def _normalize_screening_payload(payload: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    matched_skills = _normalize_string_list(payload.get("matched_skills")) or list(fallback.get("matched_skills", []))
    missing_skills = _normalize_string_list(payload.get("missing_skills")) or list(fallback.get("missing_skills", []))
    matched_preferred_skills = _normalize_string_list(payload.get("matched_preferred_skills")) or list(
        fallback.get("matched_preferred_skills", [])
    )
    strengths = _normalize_string_list(payload.get("strengths")) or list(fallback.get("strengths", []))
    risks = _normalize_string_list(payload.get("risks")) or list(fallback.get("risks", []))
    suggested_questions = _normalize_string_list(payload.get("suggested_questions")) or list(
        fallback.get("suggested_questions", [])
    )

    overall_score = _normalize_score(payload.get("overall_score"), fallback.get("overall_score", 0))
    recommended_status = str(payload.get("recommended_status") or "").strip()
    if recommended_status not in ALLOWED_SCREENING_STATUSES:
        recommended_status = str(fallback.get("recommended_status") or "Ready for Review")

    return {
        "overall_score": overall_score,
        "recommended_status": recommended_status,
        "matched_skills": matched_skills,
        "matched_preferred_skills": matched_preferred_skills,
        "missing_skills": missing_skills,
        "summary": _sanitize_text(payload.get("summary"), fallback.get("summary", "")),
        "strengths": strengths,
        "risks": risks,
        "suggested_questions": suggested_questions,
    }


def _request_json_completion(system_prompt: str, user_prompt: str) -> dict[str, Any]:
    content = _request_text_completion(system_prompt=system_prompt, user_prompt=user_prompt)
    try:
        return _extract_json_object(content)
    except (json.JSONDecodeError, ValueError) as exc:
        raise AIAssistantError(f"大模型未返回可解析的 JSON：{exc}") from exc


def _request_text_completion(system_prompt: str, user_prompt: str) -> str:
    payload = {
        "model": _get_model_name(),
        "temperature": _get_float_env("AIHR_LLM_TEMPERATURE", 0.2),
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    body = _request_chat_completion(payload)
    choices = body.get("choices") or []
    if not choices:
        raise AIAssistantError("大模型未返回候选结果。")

    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, list):
        text = "".join(part.get("text", "") for part in content if isinstance(part, dict))
    else:
        text = str(content or "")

    cleaned = text.strip()
    if not cleaned:
        raise AIAssistantError("大模型返回内容为空。")
    return cleaned


def _request_chat_completion(payload: dict[str, Any]) -> dict[str, Any]:
    request = Request(
        _build_chat_completions_url(),
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {_get_api_key()}",
            "Accept": "application/json",
        },
    )

    try:
        with urlopen(request, timeout=_get_int_env("AIHR_LLM_REQUEST_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)) as response:
            body = response.read().decode("utf-8", errors="ignore")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise AIAssistantError(f"大模型接口失败：HTTP {exc.code} {detail}") from exc
    except URLError as exc:
        raise AIAssistantError(f"大模型接口网络异常：{exc}") from exc

    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise AIAssistantError(f"大模型返回了不可解析的 JSON：{body[:200]}") from exc

    if parsed.get("error"):
        raise AIAssistantError(f"大模型接口返回错误：{parsed['error']}")
    return parsed


def _extract_json_object(content: str) -> dict[str, Any]:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, flags=re.S)
        if not match:
            raise
        return json.loads(match.group(0))


def _build_chat_completions_url() -> str:
    base_url = os.getenv("AIHR_LLM_BASE_URL", "").strip() or DEFAULT_LLM_BASE_URL
    if base_url.endswith("/chat/completions"):
        return base_url
    if base_url.endswith("/v1"):
        return f"{base_url}/chat/completions"
    return f"{base_url.rstrip('/')}/v1/chat/completions"


def _get_api_key() -> str:
    return os.getenv("AIHR_LLM_API_KEY", "").strip()


def _get_model_name() -> str:
    return os.getenv("AIHR_LLM_MODEL", "").strip() or DEFAULT_LLM_MODEL


def _normalize_score(value: Any, default: Any) -> int:
    try:
        score = int(round(float(value)))
    except (TypeError, ValueError):
        try:
            score = int(round(float(default)))
        except (TypeError, ValueError):
            score = 0
    return max(0, min(score, 100))


def _normalize_string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        chunks = re.split(r"[\n,，；;、]+", value)
    elif isinstance(value, list):
        chunks = value
    else:
        return []

    normalized: list[str] = []
    seen: set[str] = set()
    for chunk in chunks:
        item = str(chunk or "").strip()
        if not item:
            continue
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(item)
    return normalized[:6]


def _sanitize_text(value: Any, default: str) -> str:
    text = str(value or "").strip()
    return text or default


def _truncate_text(value: str, limit: int) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return f"{text[: limit - 1].rstrip()}…"


def _get_float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _get_int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default
