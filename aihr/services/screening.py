from __future__ import annotations

import re
from typing import Any, Iterable

from aihr.services.resume_parser import DEFAULT_SKILL_LEXICON

YEARS_RE = re.compile(r"(\d{1,2})(?:\+)?\s*(?:years|yrs|year)\b", re.I)
ZH_YEARS_RE = re.compile(r"(\d{1,2})(?:\+)?\s*(?:年经验|年以上|年工作经验|年)", re.I)


def screen_candidate(
    parsed_resume: dict[str, Any],
    job_requirements: str,
    preferred_skills: str = "",
    preferred_city: str = "",
) -> dict[str, Any]:
    required_skills = extract_skill_keywords(job_requirements)
    preferred_skill_set = extract_skill_keywords(preferred_skills)
    candidate_skills = {skill.lower() for skill in parsed_resume.get("skills", [])}
    matched_skills = sorted(candidate_skills & required_skills)
    missing_skills = sorted(required_skills - candidate_skills)
    matched_preferred_skills = sorted(candidate_skills & preferred_skill_set)

    required_skill_score = 0
    if required_skills:
        required_skill_score = round((len(matched_skills) / len(required_skills)) * 60)

    preferred_skill_score = 0
    if preferred_skill_set:
        preferred_skill_score = round((len(matched_preferred_skills) / len(preferred_skill_set)) * 15)

    requested_years = extract_year_requirement(job_requirements)
    candidate_years = float(parsed_resume.get("years_of_experience", 0) or 0)
    experience_score = 0
    if requested_years <= 0:
        experience_score = 15
    elif candidate_years >= requested_years:
        experience_score = 15
    elif requested_years > 0:
        experience_score = round((candidate_years / requested_years) * 15)

    location_score = 0
    if preferred_city:
        resume_city = str(parsed_resume.get("city", "") or "")
        if resume_city and preferred_city.lower() in resume_city.lower():
            location_score = 10
    else:
        location_score = 10

    profile_score = 0
    if parsed_resume.get("emails") or parsed_resume.get("phones"):
        profile_score += 5
    if parsed_resume.get("name"):
        profile_score += 5

    overall_score = min(required_skill_score + preferred_skill_score + experience_score + location_score + profile_score, 100)
    recommended_status = recommend_status(overall_score, missing_skills)

    strengths = build_strengths(parsed_resume, matched_skills, matched_preferred_skills)
    risks = build_risks(parsed_resume, missing_skills, requested_years)
    suggested_questions = build_questions(missing_skills, requested_years, candidate_years)

    return {
        "overall_score": overall_score,
        "recommended_status": recommended_status,
        "matched_skills": matched_skills,
        "matched_preferred_skills": matched_preferred_skills,
        "missing_skills": missing_skills,
        "summary": build_summary(overall_score, matched_skills, missing_skills, candidate_years),
        "strengths": strengths,
        "risks": risks,
        "suggested_questions": suggested_questions,
    }


def extract_skill_keywords(text: str, extra_lexicon: Iterable[str] | None = None) -> set[str]:
    lexicon = {skill.lower() for skill in DEFAULT_SKILL_LEXICON}
    if extra_lexicon:
        lexicon.update(skill.lower() for skill in extra_lexicon)

    lowered = (text or "").lower()
    found = {skill for skill in lexicon if skill in lowered}

    for chunk in re.split(r"[\n,;/，；、]", text or ""):
        chunk = chunk.strip().lower()
        if any(char.isdigit() for char in chunk):
            continue
        if any(symbol in chunk for symbol in ".:!?()[]{}。；：，"):
            continue
        if re.search(r"[\u4e00-\u9fff]", chunk):
            if chunk in lexicon:
                found.add(chunk)
            continue
        if 1 < len(chunk) <= 32 and 0 < len(chunk.split()) <= 3:
            found.add(chunk)

    return found


def extract_year_requirement(text: str) -> int:
    matches = [int(match.group(1)) for match in YEARS_RE.finditer(text or "")]
    matches.extend(int(match.group(1)) for match in ZH_YEARS_RE.finditer(text or ""))
    return max(matches, default=0)


def recommend_status(overall_score: int, missing_skills: list[str]) -> str:
    if overall_score >= 75 and len(missing_skills) <= 2:
        return "Advance"
    if overall_score >= 50:
        return "Ready for Review"
    return "Hold"


def build_strengths(
    parsed_resume: dict[str, Any],
    matched_skills: list[str],
    matched_preferred_skills: list[str],
) -> list[str]:
    strengths = []
    if matched_skills:
        strengths.append(f"核心技能匹配度较高：{format_skill_list(matched_skills[:6])}。")
    if matched_preferred_skills:
        strengths.append(f"加分项已有体现：{format_skill_list(matched_preferred_skills[:4])}。")
    years = parsed_resume.get("years_of_experience", 0)
    if years:
        strengths.append(f"简历显示约 {years:g} 年相关经验。")
    if parsed_resume.get("city"):
        strengths.append(f"候选人当前城市识别为 {parsed_resume['city']}。")
    return strengths or ["简历信息已提取，但仍需 HR 或用人经理复核。"]


def build_risks(parsed_resume: dict[str, Any], missing_skills: list[str], requested_years: int) -> list[str]:
    risks = []
    if missing_skills:
        risks.append(f"以下关键项在简历中未充分体现：{format_skill_list(missing_skills[:6])}。")
    if requested_years and float(parsed_resume.get("years_of_experience", 0) or 0) < requested_years:
        risks.append("工作年限可能低于岗位要求，建议面试时重点确认项目深度和职责范围。")
    if not parsed_resume.get("phones"):
        risks.append("未能可靠提取手机号，后续沟通前建议人工确认联系方式。")
    return risks or ["暂未发现明显风险，但仍建议结合业务场景复核。"]


def build_questions(missing_skills: list[str], requested_years: int, candidate_years: float) -> list[str]:
    questions = []
    for skill in missing_skills[:3]:
        questions.append(f"请候选人举例说明在 {skill} 方面的实际项目经历、职责和结果。")
    if requested_years and candidate_years < requested_years:
        questions.append("请确认候选人是否独立承担过与当前岗位级别相当的职责范围。")
    if not questions:
        questions.append("请围绕其最强的一段项目经历追问具体指标、产出和业务影响。")
    return questions


def build_summary(overall_score: int, matched_skills: list[str], missing_skills: list[str], candidate_years: float) -> str:
    matched_text = format_skill_list(matched_skills[:4]) if matched_skills else "暂无足够明确的技能证据"
    missing_text = format_skill_list(missing_skills[:3]) if missing_skills else "暂无明显缺口"
    return (
        f"AI 启发式匹配分为 {overall_score}/100。"
        f" 当前优势集中在：{matched_text}。"
        f" 主要待确认项：{missing_text}。"
        f" 简历识别到约 {candidate_years:g} 年相关经验。"
    )


def build_agency_brief(payload: dict[str, Any]) -> str:
    title = payload.get("designation") or payload.get("job_title") or "待定岗位"
    department = payload.get("department") or "待定"
    work_city = payload.get("work_city") or payload.get("aihr_work_city") or "待定"
    work_mode = payload.get("work_mode") or payload.get("aihr_work_mode") or "待定"
    work_schedule = payload.get("work_schedule") or payload.get("aihr_work_schedule") or "待定"
    salary_currency = payload.get("salary_currency") or payload.get("aihr_salary_currency") or ""
    salary_min = payload.get("salary_min") or payload.get("aihr_salary_min") or ""
    salary_max = payload.get("salary_max") or payload.get("aihr_salary_max") or ""
    must_have = payload.get("must_have_skills") or payload.get("aihr_must_have_skills") or ""
    nice_to_have = payload.get("nice_to_have_skills") or payload.get("aihr_nice_to_have_skills") or ""
    hiring_goal = payload.get("reason_for_requesting") or payload.get("hiring_goal") or ""

    salary_line = "待定"
    if salary_min or salary_max:
        salary_line = f"{salary_currency} {salary_min} - {salary_max}".strip()

    return (
        f"岗位名称：{title}\n"
        f"所属部门：{department}\n"
        f"工作模式：{work_mode}\n"
        f"工作城市：{work_city}\n"
        f"工作时间：{work_schedule}\n"
        f"薪资范围：{salary_line}\n"
        f"招聘目标：{hiring_goal or '补充团队编制并支持业务交付'}\n"
        f"必备要求：{must_have or '待补充'}\n"
        f"加分项：{nice_to_have or '无'}\n"
        "代理说明：请优先提交 PDF 简历，并补充候选人当前薪资、期望薪资、到岗时间和最早可面试时间。"
    )


def format_skill_list(skills: list[str]) -> str:
    if not skills:
        return "暂无"
    return "、".join(skills)
