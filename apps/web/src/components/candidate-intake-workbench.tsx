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

export function CandidateIntakeWorkbench(props: { disabled?: boolean }) {
  const { disabled = false } = props;
  const router = useRouter();
  const [form, setForm] = useState({
    name: "",
    role: "",
    city: "上海",
    experience: "5 年",
    owner: "待分配",
    source: "手动录入",
    status: "待经理复核",
    nextAction: "运行 AI 初筛",
    score: 86,
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
      const response = await fetch(`${browserApiBaseUrl}/api/candidates`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          name: form.name,
          role: form.role,
          city: form.city,
          experience: form.experience,
          owner: form.owner,
          source: form.source,
          status: form.status,
          next_action: form.nextAction,
          score: form.score,
          skills: parseSkills(form.skills),
        }),
      });

      if (!response.ok) {
        throw new Error(`API ${response.status}`);
      }

      const payload = (await response.json()) as { id: string; name: string };
      setSuccess(`已创建 ${payload.name}（${payload.id}）`);
      setForm((current) => ({
        ...current,
        name: "",
        role: "",
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
            <span>姓名</span>
            <input
              className="text-input"
              disabled={pending || disabled}
              required
              value={form.name}
              onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
            />
          </label>
          <label className="field-stack">
            <span>岗位</span>
            <input
              className="text-input"
              disabled={pending || disabled}
              required
              value={form.role}
              onChange={(event) => setForm((current) => ({ ...current, role: event.target.value }))}
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
            <span>经验</span>
            <input
              className="text-input"
              disabled={pending || disabled}
              value={form.experience}
              onChange={(event) => setForm((current) => ({ ...current, experience: event.target.value }))}
            />
          </label>
          <label className="field-stack">
            <span>匹配分</span>
            <input
              className="text-input"
              disabled={pending || disabled}
              max={100}
              min={0}
              step={1}
              type="number"
              value={form.score}
              onChange={(event) => setForm((current) => ({ ...current, score: Number.parseInt(event.target.value, 10) || 0 }))}
            />
          </label>
          <label className="field-stack">
            <span>来源</span>
            <input
              className="text-input"
              disabled={pending || disabled}
              value={form.source}
              onChange={(event) => setForm((current) => ({ ...current, source: event.target.value }))}
            />
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

        <div className="form-actions">
          <button className="primary-button" disabled={pending || disabled} type="submit">
            {disabled ? "启动 API 后可用" : pending ? "录入中..." : "快速录入候选人"}
          </button>
          <p className="subtle-text">写入 SQLite 持久层，刷新后列表可见。</p>
        </div>
      </form>

      {error ? <div className="error-banner">候选人录入失败：{error}</div> : null}
      {success ? <div className="success-banner">{success}</div> : null}
    </div>
  );
}
