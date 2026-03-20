from __future__ import annotations

import re
from typing import Any, Iterable

from aihr.services.resume_parser import DEFAULT_SKILL_LEXICON

YEARS_RE = re.compile(r"(\d{1,2})(?:\+)?\s*(?:years|yrs|year)\b", re.I)


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

    for chunk in re.split(r"[\n,;/]", text or ""):
        chunk = chunk.strip().lower()
        if any(char.isdigit() for char in chunk):
            continue
        if 1 < len(chunk) <= 32 and 0 < len(chunk.split()) <= 3:
            found.add(chunk)

    return found


def extract_year_requirement(text: str) -> int:
    matches = [int(match.group(1)) for match in YEARS_RE.finditer(text or "")]
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
        strengths.append(f"Core skill overlap is strong: {', '.join(matched_skills[:6])}.")
    if matched_preferred_skills:
        strengths.append(f"Preferred skills present: {', '.join(matched_preferred_skills[:4])}.")
    years = parsed_resume.get("years_of_experience", 0)
    if years:
        strengths.append(f"Resume indicates about {years} years of experience.")
    if parsed_resume.get("city"):
        strengths.append(f"Candidate location captured as {parsed_resume['city']}.")
    return strengths or ["Profile data is present but still needs human review."]


def build_risks(parsed_resume: dict[str, Any], missing_skills: list[str], requested_years: int) -> list[str]:
    risks = []
    if missing_skills:
        risks.append(f"Missing or not evidenced in resume: {', '.join(missing_skills[:6])}.")
    if requested_years and float(parsed_resume.get("years_of_experience", 0) or 0) < requested_years:
        risks.append("Experience level may be below the requested threshold.")
    if not parsed_resume.get("phones"):
        risks.append("Phone number was not confidently extracted from the resume.")
    return risks or ["No major risk was found by the heuristic screen."]


def build_questions(missing_skills: list[str], requested_years: int, candidate_years: float) -> list[str]:
    questions = []
    for skill in missing_skills[:3]:
        questions.append(f"Ask for a concrete example of hands-on work using {skill}.")
    if requested_years and candidate_years < requested_years:
        questions.append("Clarify depth of ownership compared with the role seniority target.")
    if not questions:
        questions.append("Probe the strongest project in the resume and quantify outcomes.")
    return questions


def build_summary(overall_score: int, matched_skills: list[str], missing_skills: list[str], candidate_years: float) -> str:
    matched_text = ", ".join(matched_skills[:4]) if matched_skills else "limited explicit skill evidence"
    missing_text = ", ".join(missing_skills[:3]) if missing_skills else "no major missing keyword"
    return (
        f"Heuristic match score {overall_score}/100. "
        f"Strongest overlap: {matched_text}. "
        f"Main gap: {missing_text}. "
        f"Resume suggests about {candidate_years:g} years of experience."
    )


def build_agency_brief(payload: dict[str, Any]) -> str:
    title = payload.get("designation") or payload.get("job_title") or "New Role"
    department = payload.get("department") or "TBD"
    work_city = payload.get("work_city") or payload.get("aihr_work_city") or "TBD"
    work_mode = payload.get("work_mode") or payload.get("aihr_work_mode") or "TBD"
    work_schedule = payload.get("work_schedule") or payload.get("aihr_work_schedule") or "TBD"
    salary_currency = payload.get("salary_currency") or payload.get("aihr_salary_currency") or ""
    salary_min = payload.get("salary_min") or payload.get("aihr_salary_min") or ""
    salary_max = payload.get("salary_max") or payload.get("aihr_salary_max") or ""
    must_have = payload.get("must_have_skills") or payload.get("aihr_must_have_skills") or ""
    nice_to_have = payload.get("nice_to_have_skills") or payload.get("aihr_nice_to_have_skills") or ""
    hiring_goal = payload.get("reason_for_requesting") or payload.get("hiring_goal") or ""

    salary_line = "TBD"
    if salary_min or salary_max:
        salary_line = f"{salary_currency} {salary_min} - {salary_max}".strip()

    return (
        f"Role: {title}\n"
        f"Department: {department}\n"
        f"Work Model: {work_mode}\n"
        f"City: {work_city}\n"
        f"Schedule: {work_schedule}\n"
        f"Salary Range: {salary_line}\n"
        f"Hiring Goal: {hiring_goal}\n"
        f"Must Have: {must_have}\n"
        f"Nice To Have: {nice_to_have}\n"
        "Agency Notes: please submit resumes in PDF and include current salary, notice period, and earliest interview slot."
    )
