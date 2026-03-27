"use client";

import { useState } from "react";

import { browserApiBaseUrl, type AgencyBriefResponse } from "@/lib/api";
import type { JobRecord } from "@/lib/site-data";

export function AgencyBriefWorkbench(props: {
  job: JobRecord;
  disabled?: boolean;
}) {
  const { job, disabled = false } = props;
  const [form, setForm] = useState({
    jobTitle: job.title,
    department: job.team,
    workCity: job.location,
    workMode: job.mode,
    workSchedule: "标准工作制",
    salaryMin: job.urgency === "critical" ? "40k" : "30k",
    salaryMax: job.urgency === "critical" ? "65k" : "45k",
    mustHaveSkills: job.skills.slice(0, 3).join(", "),
    niceToHaveSkills: job.skills.slice(3).join(", "),
    reason: job.summary,
  });
  const [result, setResult] = useState<AgencyBriefResponse | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError("");

    try {
      const response = await fetch(`${browserApiBaseUrl}/api/requisitions/agency-brief`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          job_title: form.jobTitle,
          designation: form.jobTitle,
          department: form.department,
          aihr_work_city: form.workCity,
          aihr_work_mode: form.workMode,
          aihr_work_schedule: form.workSchedule,
          aihr_salary_currency: "CNY",
          aihr_salary_min: form.salaryMin,
          aihr_salary_max: form.salaryMax,
          aihr_must_have_skills: form.mustHaveSkills,
          aihr_nice_to_have_skills: form.niceToHaveSkills,
          reason_for_requesting: form.reason,
        }),
      });

      if (!response.ok) {
        throw new Error(`API ${response.status}`);
      }

      setResult((await response.json()) as AgencyBriefResponse);
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
            <span>岗位名称</span>
            <input
              className="text-input"
              disabled={pending || disabled}
              value={form.jobTitle}
              onChange={(event) => setForm((current) => ({ ...current, jobTitle: event.target.value }))}
            />
          </label>
          <label className="field-stack">
            <span>部门</span>
            <input
              className="text-input"
              disabled={pending || disabled}
              value={form.department}
              onChange={(event) => setForm((current) => ({ ...current, department: event.target.value }))}
            />
          </label>
          <label className="field-stack">
            <span>工作城市</span>
            <input
              className="text-input"
              disabled={pending || disabled}
              value={form.workCity}
              onChange={(event) => setForm((current) => ({ ...current, workCity: event.target.value }))}
            />
          </label>
          <label className="field-stack">
            <span>工作模式</span>
            <input
              className="text-input"
              disabled={pending || disabled}
              value={form.workMode}
              onChange={(event) => setForm((current) => ({ ...current, workMode: event.target.value }))}
            />
          </label>
          <label className="field-stack">
            <span>薪资下限</span>
            <input
              className="text-input"
              disabled={pending || disabled}
              value={form.salaryMin}
              onChange={(event) => setForm((current) => ({ ...current, salaryMin: event.target.value }))}
            />
          </label>
          <label className="field-stack">
            <span>薪资上限</span>
            <input
              className="text-input"
              disabled={pending || disabled}
              value={form.salaryMax}
              onChange={(event) => setForm((current) => ({ ...current, salaryMax: event.target.value }))}
            />
          </label>
        </div>

        <label className="field-stack">
          <span>必备技能</span>
          <input
            className="text-input"
            disabled={pending || disabled}
            value={form.mustHaveSkills}
            onChange={(event) => setForm((current) => ({ ...current, mustHaveSkills: event.target.value }))}
          />
        </label>

        <label className="field-stack">
          <span>加分项</span>
          <input
            className="text-input"
            disabled={pending || disabled}
            value={form.niceToHaveSkills}
            onChange={(event) => setForm((current) => ({ ...current, niceToHaveSkills: event.target.value }))}
          />
        </label>

        <label className="field-stack">
          <span>招聘目标</span>
          <textarea
            className="text-area"
            disabled={pending || disabled}
            rows={4}
            value={form.reason}
            onChange={(event) => setForm((current) => ({ ...current, reason: event.target.value }))}
          />
        </label>

        <div className="form-actions">
          <button className="primary-button" disabled={pending || disabled} type="submit">
            {disabled ? "启动 API 后可用" : pending ? "生成中..." : "生成猎头 brief"}
          </button>
          <p className="subtle-text">直接复用旧仓库的岗位 payload 和 brief 生成逻辑。</p>
        </div>
      </form>

      {error ? <div className="error-banner">岗位 brief 生成失败：{error}</div> : null}

      {result ? (
        <article className="result-card">
          <p className="eyebrow">Agency Brief</p>
          <pre className="result-pre">{result.brief}</pre>
        </article>
      ) : null}
    </div>
  );
}
