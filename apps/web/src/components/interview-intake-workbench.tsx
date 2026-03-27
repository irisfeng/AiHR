"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { browserApiBaseUrl } from "@/lib/api";

export function InterviewIntakeWorkbench(props: { disabled?: boolean }) {
  const { disabled = false } = props;
  const router = useRouter();
  const [form, setForm] = useState({
    candidateName: "",
    role: "",
    round: "技术一面",
    mode: "视频",
    timeLabel: "03-29 14:00",
    interviewer: "待分配",
    status: "已安排",
    decisionWindow: "面试后 24 小时",
    packStatus: "待补充",
    summary: "",
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
      const response = await fetch(`${browserApiBaseUrl}/api/interviews`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          candidate_name: form.candidateName,
          role: form.role,
          round: form.round,
          mode: form.mode,
          time_label: form.timeLabel,
          interviewer: form.interviewer,
          status: form.status,
          decision_window: form.decisionWindow,
          pack_status: form.packStatus,
          summary: form.summary,
        }),
      });

      if (!response.ok) {
        throw new Error(`API ${response.status}`);
      }

      const payload = (await response.json()) as { id: string; candidateName: string };
      setSuccess(`已安排 ${payload.candidateName}（${payload.id}）`);
      setForm((current) => ({
        ...current,
        candidateName: "",
        role: "",
        summary: "",
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
            <span>候选人</span>
            <input
              className="text-input"
              disabled={pending || disabled}
              required
              value={form.candidateName}
              onChange={(event) => setForm((current) => ({ ...current, candidateName: event.target.value }))}
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
            <span>轮次</span>
            <input
              className="text-input"
              disabled={pending || disabled}
              value={form.round}
              onChange={(event) => setForm((current) => ({ ...current, round: event.target.value }))}
            />
          </label>
          <label className="field-stack">
            <span>形式</span>
            <input
              className="text-input"
              disabled={pending || disabled}
              value={form.mode}
              onChange={(event) => setForm((current) => ({ ...current, mode: event.target.value }))}
            />
          </label>
          <label className="field-stack">
            <span>时间</span>
            <input
              className="text-input"
              disabled={pending || disabled}
              value={form.timeLabel}
              onChange={(event) => setForm((current) => ({ ...current, timeLabel: event.target.value }))}
            />
          </label>
          <label className="field-stack">
            <span>面试官</span>
            <input
              className="text-input"
              disabled={pending || disabled}
              value={form.interviewer}
              onChange={(event) => setForm((current) => ({ ...current, interviewer: event.target.value }))}
            />
          </label>
        </div>

        <label className="field-stack">
          <span>面试摘要</span>
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
            {disabled ? "启动 API 后可用" : pending ? "安排中..." : "快速安排面试"}
          </button>
          <p className="subtle-text">写入持久层并同步更新对应岗位的面试计数。</p>
        </div>
      </form>

      {error ? <div className="error-banner">面试安排失败：{error}</div> : null}
      {success ? <div className="success-banner">{success}</div> : null}
    </div>
  );
}
