"use client";

import { useState } from "react";

import { browserApiBaseUrl, type ScreeningPreviewResponse } from "@/lib/api";
import type { CandidateRecord } from "@/lib/site-data";

function toSkillText(skills: string[]) {
  return skills.join(", ");
}

function fromSkillText(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function ScreeningPreviewWorkbench(props: {
  candidate: CandidateRecord;
  disabled?: boolean;
}) {
  const { candidate, disabled = false } = props;
  const [form, setForm] = useState({
    name: candidate.name,
    city: candidate.city,
    skills: toSkillText(candidate.skills),
    yearsOfExperience: Number.parseFloat(candidate.experience) || 0,
    requirements: `${candidate.role}；需要 ${candidate.skills.slice(0, 3).join("、")}；5 years；能独立推进核心项目。`,
    preferredSkills: candidate.skills.slice(3).join(", "),
    preferredCity: candidate.city,
  });
  const [result, setResult] = useState<ScreeningPreviewResponse | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError("");

    try {
      const response = await fetch(`${browserApiBaseUrl}/api/screening/preview`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          name: form.name,
          city: form.city,
          skills: fromSkillText(form.skills),
          years_of_experience: form.yearsOfExperience,
          requirements: form.requirements,
          preferred_skills: form.preferredSkills,
          preferred_city: form.preferredCity,
        }),
      });

      if (!response.ok) {
        throw new Error(`API ${response.status}`);
      }

      setResult((await response.json()) as ScreeningPreviewResponse);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "请求失败");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="stack-list">
      <form className="workbench-form" onSubmit={handleSubmit}>
        <div className="field-grid">
          <label className="field-stack">
            <span>候选人</span>
            <input
              className="text-input"
              disabled={pending || disabled}
              value={form.name}
              onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
            />
          </label>
          <label className="field-stack">
            <span>城市</span>
            <input
              className="text-input"
              disabled={pending || disabled}
              value={form.city}
              onChange={(event) => setForm((current) => ({ ...current, city: event.target.value }))}
            />
          </label>
          <label className="field-stack">
            <span>年限</span>
            <input
              className="text-input"
              disabled={pending || disabled}
              min={0}
              step={0.5}
              type="number"
              value={form.yearsOfExperience}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  yearsOfExperience: Number.parseFloat(event.target.value) || 0,
                }))
              }
            />
          </label>
          <label className="field-stack">
            <span>优选城市</span>
            <input
              className="text-input"
              disabled={pending || disabled}
              value={form.preferredCity}
              onChange={(event) => setForm((current) => ({ ...current, preferredCity: event.target.value }))}
            />
          </label>
        </div>

        <label className="field-stack">
          <span>技能</span>
          <input
            className="text-input"
            disabled={pending || disabled}
            value={form.skills}
            onChange={(event) => setForm((current) => ({ ...current, skills: event.target.value }))}
          />
        </label>

        <label className="field-stack">
          <span>岗位要求</span>
          <textarea
            className="text-area"
            disabled={pending || disabled}
            rows={5}
            value={form.requirements}
            onChange={(event) => setForm((current) => ({ ...current, requirements: event.target.value }))}
          />
        </label>

        <label className="field-stack">
          <span>加分项</span>
          <textarea
            className="text-area"
            disabled={pending || disabled}
            rows={3}
            value={form.preferredSkills}
            onChange={(event) => setForm((current) => ({ ...current, preferredSkills: event.target.value }))}
          />
        </label>

        <div className="form-actions">
          <button className="primary-button" disabled={pending || disabled} type="submit">
            {disabled ? "启动 API 后可用" : pending ? "生成中..." : "预演初筛结果"}
          </button>
          <p className="subtle-text">直接调 FastAPI 预演筛选分、缺口和下一步动作。</p>
        </div>
      </form>

      {error ? <div className="error-banner">初筛预演失败：{error}</div> : null}

      {result ? (
        <article className="result-card">
          <div className="compact-card__top">
            <div>
              <p className="eyebrow">Preview Result</p>
              <h4>{result.recommended_status}</h4>
            </div>
            <div className="score-badge">{result.overall_score}</div>
          </div>
          <p className="result-summary">{result.summary}</p>
          <div className="inline-chip-list">
            <span className="tag-chip">下一步：{result.next_action}</span>
            {result.matched_skills.map((item) => (
              <span key={item} className="tag-chip">
                匹配 {item}
              </span>
            ))}
          </div>
          <div className="candidate-card__body">
            <div>
              <p className="eyebrow">风险</p>
              <ul className="bullet-list bullet-list--soft">
                {result.risks.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
            <div>
              <p className="eyebrow">建议追问</p>
              <ul className="bullet-list">
                {result.suggested_questions.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          </div>
        </article>
      ) : null}
    </div>
  );
}
