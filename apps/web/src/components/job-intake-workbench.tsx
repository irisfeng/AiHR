"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { browserApiBaseUrl } from "@/lib/api";

function parseSkills(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function JobIntakeWorkbench(props: { disabled?: boolean }) {
  const { disabled = false } = props;
  const router = useRouter();
  const [form, setForm] = useState({
    title: "",
    team: "平台研发",
    location: "上海",
    mode: "Hybrid",
    headcount: 1,
    stage: "开放招聘",
    owner: "待分配",
    urgency: "high",
    summary: "",
    skills: "",
  });
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError("");
    setSuccess("");

    try {
      const response = await fetch(`${browserApiBaseUrl}/api/jobs`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          title: form.title,
          team: form.team,
          location: form.location,
          mode: form.mode,
          headcount: form.headcount,
          stage: form.stage,
          owner: form.owner,
          urgency: form.urgency,
          summary: form.summary,
          skills: parseSkills(form.skills),
        }),
      });

      if (!response.ok) {
        throw new Error(`API ${response.status}`);
      }

      const payload = (await response.json()) as { id: string; title: string };
      setSuccess(`已创建 ${payload.title}（${payload.id}）`);
      setForm((current) => ({
        ...current,
        title: "",
        summary: "",
        skills: "",
      }));
      router.refresh();
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
              required
              value={form.title}
              onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))}
            />
          </label>
          <label className="field-stack">
            <span>团队</span>
            <input
              className="text-input"
              disabled={pending || disabled}
              value={form.team}
              onChange={(event) => setForm((current) => ({ ...current, team: event.target.value }))}
            />
          </label>
          <label className="field-stack">
            <span>城市</span>
            <input
              className="text-input"
              disabled={pending || disabled}
              value={form.location}
              onChange={(event) => setForm((current) => ({ ...current, location: event.target.value }))}
            />
          </label>
          <label className="field-stack">
            <span>工作模式</span>
            <input
              className="text-input"
              disabled={pending || disabled}
              value={form.mode}
              onChange={(event) => setForm((current) => ({ ...current, mode: event.target.value }))}
            />
          </label>
          <label className="field-stack">
            <span>HC</span>
            <input
              className="text-input"
              disabled={pending || disabled}
              min={1}
              step={1}
              type="number"
              value={form.headcount}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  headcount: Number.parseInt(event.target.value, 10) || 1,
                }))
              }
            />
          </label>
          <label className="field-stack">
            <span>紧急度</span>
            <select
              className="text-input"
              disabled={pending || disabled}
              value={form.urgency}
              onChange={(event) => setForm((current) => ({ ...current, urgency: event.target.value }))}
            >
              <option value="critical">critical</option>
              <option value="high">high</option>
              <option value="medium">medium</option>
            </select>
          </label>
        </div>

        <label className="field-stack">
          <span>技能</span>
          <input
            className="text-input"
            disabled={pending || disabled}
            placeholder="Python, FastAPI, PostgreSQL"
            value={form.skills}
            onChange={(event) => setForm((current) => ({ ...current, skills: event.target.value }))}
          />
        </label>

        <label className="field-stack">
          <span>岗位摘要</span>
          <textarea
            className="text-area"
            disabled={pending || disabled}
            rows={4}
            value={form.summary}
            onChange={(event) => setForm((current) => ({ ...current, summary: event.target.value }))}
          />
        </label>

        <div className="form-actions">
          <button className="primary-button" disabled={pending || disabled} type="submit">
            {disabled ? "启动 API 后可用" : pending ? "创建中..." : "快速录入岗位"}
          </button>
          <p className="subtle-text">写入 SQLite 持久层，刷新后岗位卡片和总览统计会更新。</p>
        </div>
      </form>

      {error ? <div className="error-banner">岗位录入失败：{error}</div> : null}
      {success ? <div className="success-banner">{success}</div> : null}
    </div>
  );
}
