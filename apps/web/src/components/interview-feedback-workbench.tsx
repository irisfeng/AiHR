"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { browserApiBaseUrl } from "@/lib/api";
import type { InterviewRecord } from "@/lib/site-data";

function parseList(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function defaultNextStep(decision: string) {
  if (decision === "淘汰") {
    return "同步淘汰结论";
  }
  if (decision === "待补面") {
    return "补充信息后再决策";
  }
  return "安排下一轮面试";
}

export function InterviewFeedbackWorkbench(props: { interviews: InterviewRecord[]; disabled?: boolean }) {
  const { interviews, disabled = false } = props;
  const router = useRouter();
  const actionableInterviews = useMemo(
    () => interviews.filter((item) => !["已通过", "已淘汰"].includes(item.status)),
    [interviews],
  );
  const [form, setForm] = useState({
    interviewId: actionableInterviews[0]?.id ?? "",
    decision: "通过",
    summary: "",
    nextStep: "安排下一轮面试",
    strengths: "",
    concerns: "",
    actor: actionableInterviews[0]?.interviewer ?? "面试官",
  });
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const selectedInterview = actionableInterviews.find((item) => item.id === form.interviewId) ?? actionableInterviews[0];

  useEffect(() => {
    if (!selectedInterview) {
      return;
    }
    setForm((current) => ({
      ...current,
      interviewId: current.interviewId || selectedInterview.id,
      actor: selectedInterview.interviewer || current.actor,
    }));
  }, [selectedInterview]);

  useEffect(() => {
    setForm((current) => ({
      ...current,
      nextStep: defaultNextStep(current.decision),
    }));
  }, [form.decision]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!form.interviewId) {
      setError("没有可提交反馈的面试记录");
      return;
    }

    setPending(true);
    setError("");
    setSuccess("");

    try {
      const response = await fetch(`${browserApiBaseUrl}/api/interviews/${form.interviewId}/feedback`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          decision: form.decision,
          summary: form.summary,
          strengths: parseList(form.strengths),
          concerns: parseList(form.concerns),
          next_step: form.nextStep,
          actor: form.actor,
        }),
      });

      if (!response.ok) {
        throw new Error(`API ${response.status}`);
      }

      const payload = (await response.json()) as {
        interview: { candidateName: string; status: string };
        candidate: { nextAction: string } | null;
      };
      setSuccess(
        `已同步 ${payload.interview.candidateName} 的反馈，当前状态 ${payload.interview.status}${
          payload.candidate ? `，下一步：${payload.candidate.nextAction}` : ""
        }`,
      );
      setForm((current) => ({
        ...current,
        summary: "",
        strengths: "",
        concerns: "",
      }));
      router.refresh();
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "请求失败");
    } finally {
      setPending(false);
    }
  }

  if (!actionableInterviews.length) {
    return <p className="subtle-text">当前没有待处理反馈的面试，后续这里会集中处理面试结论。</p>;
  }

  return (
    <div className="stack-list">
      {selectedInterview ? (
        <article className="note-card">
          <div className="compact-card__top">
            <h4>
              {selectedInterview.candidateName} · {selectedInterview.round}
            </h4>
            <span className="status-pill status-pill--warning">{selectedInterview.status}</span>
          </div>
          <p>
            {selectedInterview.role} · {selectedInterview.time} · {selectedInterview.interviewer}
          </p>
          <small>{selectedInterview.summary}</small>
        </article>
      ) : null}

      <form className="workbench-form" onSubmit={handleSubmit}>
        <div className="field-grid">
          <label className="field-stack">
            <span>面试记录</span>
            <select
              className="text-input"
              disabled={pending || disabled}
              value={form.interviewId}
              onChange={(event) => setForm((current) => ({ ...current, interviewId: event.target.value }))}
            >
              {actionableInterviews.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.candidateName} · {item.round}
                </option>
              ))}
            </select>
          </label>
          <label className="field-stack">
            <span>结论</span>
            <select
              className="text-input"
              disabled={pending || disabled}
              value={form.decision}
              onChange={(event) => setForm((current) => ({ ...current, decision: event.target.value }))}
            >
              <option value="通过">通过</option>
              <option value="待补面">待补面</option>
              <option value="淘汰">淘汰</option>
            </select>
          </label>
          <label className="field-stack">
            <span>下一步</span>
            <input
              className="text-input"
              disabled={pending || disabled}
              value={form.nextStep}
              onChange={(event) => setForm((current) => ({ ...current, nextStep: event.target.value }))}
            />
          </label>
          <label className="field-stack">
            <span>反馈人</span>
            <input
              className="text-input"
              disabled={pending || disabled}
              value={form.actor}
              onChange={(event) => setForm((current) => ({ ...current, actor: event.target.value }))}
            />
          </label>
        </div>

        <label className="field-stack">
          <span>反馈摘要</span>
          <textarea
            className="text-area"
            disabled={pending || disabled}
            required
            rows={4}
            value={form.summary}
            onChange={(event) => setForm((current) => ({ ...current, summary: event.target.value }))}
          />
        </label>

        <div className="field-grid">
          <label className="field-stack">
            <span>亮点</span>
            <input
              className="text-input"
              disabled={pending || disabled}
              placeholder="工程化, 成本优化"
              value={form.strengths}
              onChange={(event) => setForm((current) => ({ ...current, strengths: event.target.value }))}
            />
          </label>
          <label className="field-stack">
            <span>风险</span>
            <input
              className="text-input"
              disabled={pending || disabled}
              placeholder="沟通, 补问项"
              value={form.concerns}
              onChange={(event) => setForm((current) => ({ ...current, concerns: event.target.value }))}
            />
          </label>
        </div>

        <div className="form-actions">
          <button className="primary-button" disabled={pending || disabled} type="submit">
            {disabled ? "启动 API 后可用" : pending ? "同步中..." : "提交面试反馈"}
          </button>
          <p className="subtle-text">提交后会同步更新候选人状态和时间线。</p>
        </div>
      </form>

      {error ? <div className="error-banner">反馈提交失败：{error}</div> : null}
      {success ? <div className="success-banner">{success}</div> : null}
    </div>
  );
}
