"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { browserApiBaseUrl, type CandidateReviewRequest, type CandidateReviewResponse } from "@/lib/api";
import type { CandidateRecord, InterviewRecord } from "@/lib/site-data";
import { StatusPill, TagList } from "@/components/chrome";

type ReviewDecision = CandidateReviewRequest["decision"];

function candidateStatusTone(status: string): "positive" | "warning" | "accent" | "neutral" {
  if (status.includes("推进")) {
    return "positive";
  }
  if (status.includes("补充") || status.includes("观察")) {
    return "warning";
  }
  if (status.includes("淘汰") || status.includes("暂不")) {
    return "neutral";
  }
  return "accent";
}

function getCandidateKey(candidate: CandidateRecord) {
  return `${candidate.name}::${candidate.role}`;
}

function buildDefaultForm(candidate: CandidateRecord): CandidateReviewRequest {
  const advance = candidate.status === "建议推进" || candidate.status === "待经理复核";
  return {
    decision: advance ? "advance" : "hold",
    summary: "",
    actor: candidate.owner,
    next_step: advance ? "安排技术一面" : candidate.nextAction,
    schedule_interview: advance,
    interview_round: "技术一面",
    interview_time: "03-31 15:00",
    interviewer: candidate.owner,
    interview_mode: "视频",
    interview_summary: "",
    decision_window: "面试后 24 小时",
    pack_status: "待补充",
  };
}

export function CandidateReviewWorkbench(props: {
  candidates: CandidateRecord[];
  interviews: InterviewRecord[];
  disabled?: boolean;
  reviewScope?: "general" | "manager";
}) {
  const { candidates, interviews, disabled = false, reviewScope = "general" } = props;
  const router = useRouter();
  const activeInterviewKeys = useMemo(
    () =>
      new Set(
        interviews
          .filter((item) => !["已淘汰"].includes(item.status))
          .map((item) => `${item.candidateName}::${item.role}`),
      ),
    [interviews],
  );
  const queueCandidates = useMemo(
    () => {
      const base = candidates
        .filter((candidate) => !candidate.status.includes("Offer"))
        .filter((candidate) => candidate.status !== "面试中");

      if (reviewScope === "manager") {
        return base.sort((left, right) => right.score - left.score);
      }

      return base
        .filter((candidate) => !activeInterviewKeys.has(getCandidateKey(candidate)))
        .sort((left, right) => right.score - left.score);
    },
    [activeInterviewKeys, candidates, reviewScope],
  );
  const [selectedCandidateId, setSelectedCandidateId] = useState(queueCandidates[0]?.id ?? "");
  const selectedCandidate = queueCandidates.find((candidate) => candidate.id === selectedCandidateId) ?? null;
  const [form, setForm] = useState<CandidateReviewRequest | null>(
    selectedCandidate ? buildDefaultForm(selectedCandidate) : null,
  );
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    if (!queueCandidates.length) {
      setSelectedCandidateId("");
      setForm(null);
      return;
    }
    if (!selectedCandidateId || !queueCandidates.some((candidate) => candidate.id === selectedCandidateId)) {
      setSelectedCandidateId(queueCandidates[0].id);
    }
  }, [queueCandidates, selectedCandidateId]);

  useEffect(() => {
    if (!selectedCandidate) {
      setForm(null);
      return;
    }
    setForm(buildDefaultForm(selectedCandidate));
  }, [selectedCandidate]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedCandidate || !form) {
      setError("当前没有可复核候选人");
      return;
    }

    setPending(true);
    setError("");
    setSuccess("");

    try {
      const response = await fetch(`${browserApiBaseUrl}/api/candidates/${selectedCandidate.id}/review`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(form),
      });

      if (!response.ok) {
        throw new Error(`API ${response.status}`);
      }

      const payload = (await response.json()) as CandidateReviewResponse;
      setSuccess(
        payload.interview
          ? `已复核 ${payload.candidate.name}，并安排 ${payload.interview.round} · ${payload.interview.time}`
          : `已复核 ${payload.candidate.name}，当前状态 ${payload.candidate.status}`,
      );
      router.refresh();
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "请求失败");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="stack-list">
      <div className="stack-list">
        {queueCandidates.length ? (
          queueCandidates.map((candidate) => (
            <button
              className={`note-card note-card--interactive${selectedCandidateId === candidate.id ? " note-card--active" : ""}`}
              key={candidate.id}
              type="button"
              onClick={() => {
                setSelectedCandidateId(candidate.id);
                setError("");
                setSuccess("");
              }}
            >
              <div className="compact-card__top">
                <div>
                  <h4>{candidate.name}</h4>
                  <p className="subtle-text">
                    {candidate.role} · {candidate.city} · {candidate.experience}
                  </p>
                </div>
                <div className="candidate-card__meta">
                  <StatusPill tone={candidateStatusTone(candidate.status)}>{candidate.status}</StatusPill>
                  <div className="score-badge">{candidate.score}</div>
                </div>
              </div>
              <p>{candidate.nextAction}</p>
              <small>
                来源 {candidate.source} · 负责人 {candidate.owner}
              </small>
            </button>
          ))
        ) : (
          <p className="subtle-text">
            {reviewScope === "manager"
              ? "当前没有待经理判断的候选人。"
              : "当前没有待经理处理的候选人，导入新简历或补录候选人后会自动进入这里。"}
          </p>
        )}
      </div>

      {selectedCandidate && form ? (
        <article className="result-card">
          <div className="compact-card__top">
            <div>
              <h4>
                {selectedCandidate.name} · {selectedCandidate.role}
              </h4>
              <p className="subtle-text">
                {selectedCandidate.city} · {selectedCandidate.experience} · {selectedCandidate.source}
              </p>
            </div>
            <StatusPill tone={candidateStatusTone(selectedCandidate.status)}>{selectedCandidate.status}</StatusPill>
          </div>

          <TagList items={selectedCandidate.skills} />

          <div className="candidate-card__body">
            <div>
              <p className="eyebrow">高亮证据</p>
              <ul className="bullet-list">
                {selectedCandidate.highlights.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
            <div>
              <p className="eyebrow">待确认风险</p>
              <ul className="bullet-list bullet-list--soft">
                {selectedCandidate.risks.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          </div>

          <form className="workbench-form" onSubmit={handleSubmit}>
            <div className="field-grid">
              <label className="field-stack">
                <span>复核结论</span>
                <select
                  className="text-input"
                  disabled={pending || disabled}
                  value={form.decision}
                  onChange={(event) => {
                    const decision = event.target.value as ReviewDecision;
                    setForm((current) =>
                      current
                        ? {
                            ...current,
                            decision,
                            next_step:
                              decision === "advance"
                                ? "安排技术一面"
                                : decision === "hold"
                                  ? "补充信息后再决策"
                                  : "同步淘汰结论并归档",
                            schedule_interview: decision === "advance",
                          }
                        : current,
                    );
                  }}
                >
                  <option value="advance">推进</option>
                  <option value="hold">补充信息</option>
                  <option value="reject">暂不推进</option>
                </select>
              </label>
              <label className="field-stack">
                <span>复核人</span>
                <input
                  className="text-input"
                  disabled={pending || disabled}
                  value={form.actor}
                  onChange={(event) => setForm((current) => (current ? { ...current, actor: event.target.value } : current))}
                />
              </label>
            </div>

            <label className="field-stack">
              <span>复核结论摘要</span>
              <textarea
                className="text-area"
                disabled={pending || disabled}
                rows={4}
                value={form.summary}
                onChange={(event) => setForm((current) => (current ? { ...current, summary: event.target.value } : current))}
              />
            </label>

            <label className="field-stack">
              <span>下一步动作</span>
              <input
                className="text-input"
                disabled={pending || disabled}
                value={form.next_step}
                onChange={(event) => setForm((current) => (current ? { ...current, next_step: event.target.value } : current))}
              />
            </label>

            {form.decision === "advance" ? (
              <>
                <label className="field-checkbox">
                  <input
                    checked={form.schedule_interview}
                    disabled={pending || disabled}
                    type="checkbox"
                    onChange={(event) =>
                      setForm((current) =>
                        current ? { ...current, schedule_interview: event.target.checked } : current,
                      )
                    }
                  />
                  <span>复核通过后直接安排面试</span>
                </label>

                {form.schedule_interview ? (
                  <>
                    <div className="field-grid">
                      <label className="field-stack">
                        <span>轮次</span>
                        <input
                          className="text-input"
                          disabled={pending || disabled}
                          value={form.interview_round}
                          onChange={(event) =>
                            setForm((current) => (current ? { ...current, interview_round: event.target.value } : current))
                          }
                        />
                      </label>
                      <label className="field-stack">
                        <span>面试时间</span>
                        <input
                          className="text-input"
                          disabled={pending || disabled}
                          value={form.interview_time}
                          onChange={(event) =>
                            setForm((current) => (current ? { ...current, interview_time: event.target.value } : current))
                          }
                        />
                      </label>
                      <label className="field-stack">
                        <span>面试官</span>
                        <input
                          className="text-input"
                          disabled={pending || disabled}
                          value={form.interviewer}
                          onChange={(event) =>
                            setForm((current) => (current ? { ...current, interviewer: event.target.value } : current))
                          }
                        />
                      </label>
                      <label className="field-stack">
                        <span>形式</span>
                        <input
                          className="text-input"
                          disabled={pending || disabled}
                          value={form.interview_mode}
                          onChange={(event) =>
                            setForm((current) => (current ? { ...current, interview_mode: event.target.value } : current))
                          }
                        />
                      </label>
                    </div>

                    <label className="field-stack">
                      <span>面试摘要</span>
                      <textarea
                        className="text-area"
                        disabled={pending || disabled}
                        rows={3}
                        value={form.interview_summary}
                        onChange={(event) =>
                          setForm((current) => (current ? { ...current, interview_summary: event.target.value } : current))
                        }
                      />
                    </label>
                  </>
                ) : null}
              </>
            ) : null}

            <div className="form-actions">
              <button className="primary-button" disabled={pending || disabled} type="submit">
                {disabled ? "启动 API 后可用" : pending ? "提交中..." : "提交复核"}
              </button>
              <p className="subtle-text">提交一次会同步更新候选人状态、时间线，必要时直接创建面试。</p>
            </div>
          </form>
        </article>
      ) : null}

      {error ? <div className="error-banner">经理复核失败：{error}</div> : null}
      {success ? <div className="success-banner">{success}</div> : null}
    </div>
  );
}
