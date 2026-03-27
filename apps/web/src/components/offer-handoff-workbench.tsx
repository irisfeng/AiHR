"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { browserApiBaseUrl } from "@/lib/api";
import type { CandidateRecord, JobRecord, OfferRecord } from "@/lib/site-data";

export function OfferHandoffWorkbench(props: {
  candidates: CandidateRecord[];
  jobs: JobRecord[];
  offers: OfferRecord[];
  disabled?: boolean;
}) {
  const { candidates, jobs, offers, disabled = false } = props;
  const router = useRouter();
  const candidateOptions = useMemo(
    () => candidates.filter((item) => !offers.some((offer) => offer.candidateId === item.id && offer.status !== "Rejected")),
    [candidates, offers],
  );
  const [form, setForm] = useState({
    candidateId: candidateOptions[0]?.id ?? "",
    jobId: jobs[0]?.id ?? "",
    status: "Accepted",
    salaryExpectation: "",
    compensationNotes: "",
    onboardingOwner: "",
    payrollOwner: "",
  });
  const [pending, setPending] = useState(false);
  const [actingOfferId, setActingOfferId] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  async function handleCreate(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError("");
    setSuccess("");

    try {
      const response = await fetch(`${browserApiBaseUrl}/api/offers`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          candidate_id: form.candidateId,
          job_id: form.jobId,
          status: form.status,
          salary_expectation: form.salaryExpectation,
          compensation_notes: form.compensationNotes,
          onboarding_owner: form.onboardingOwner,
          payroll_owner: form.payrollOwner,
        }),
      });

      if (!response.ok) {
        throw new Error(`API ${response.status}`);
      }

      const payload = (await response.json()) as { candidateName: string; nextAction: string };
      setSuccess(`已创建 ${payload.candidateName} 的 Offer 交接，下一步：${payload.nextAction}`);
      setForm((current) => ({
        ...current,
        candidateId: "",
        salaryExpectation: "",
        compensationNotes: "",
      }));
      router.refresh();
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "请求失败");
    } finally {
      setPending(false);
    }
  }

  async function handlePayrollReady(offerId: string) {
    setActingOfferId(offerId);
    setError("");
    setSuccess("");

    try {
      const response = await fetch(`${browserApiBaseUrl}/api/offers/${offerId}/payroll-ready`, {
        method: "POST",
      });

      if (!response.ok) {
        throw new Error(`API ${response.status}`);
      }

      const payload = (await response.json()) as { offer: { candidateName: string; nextAction: string } };
      setSuccess(`已标记 ${payload.offer.candidateName} 的薪酬交接就绪，下一步：${payload.offer.nextAction}`);
      router.refresh();
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "请求失败");
    } finally {
      setActingOfferId("");
    }
  }

  return (
    <div className="stack-list">
      <div className="stack-list">
        {offers.length ? (
          offers.map((offer) => (
            <article className="note-card" key={offer.id}>
              <div className="compact-card__top">
                <h4>
                  {offer.candidateName} · {offer.openingTitle}
                </h4>
                <span className="status-pill status-pill--accent">{offer.payrollHandoffStatus}</span>
              </div>
              <p>
                {offer.status} · 入职负责人 {offer.onboardingOwner} · 薪酬负责人 {offer.payrollOwner}
              </p>
              <small>{offer.nextAction}</small>
              {offer.payrollHandoffStatus === "Not Started" ? (
                <div className="form-actions">
                  <button
                    className="secondary-button"
                    disabled={disabled || actingOfferId === offer.id}
                    onClick={() => void handlePayrollReady(offer.id)}
                    type="button"
                  >
                    {actingOfferId === offer.id ? "更新中..." : "标记薪酬就绪"}
                  </button>
                </div>
              ) : null}
            </article>
          ))
        ) : (
          <p className="subtle-text">当前没有在途 Offer。</p>
        )}
      </div>

      <form className="workbench-form" onSubmit={handleCreate}>
        <div className="field-grid">
          <label className="field-stack">
            <span>候选人</span>
            <select
              className="text-input"
              disabled={pending || disabled}
              required
              value={form.candidateId}
              onChange={(event) => setForm((current) => ({ ...current, candidateId: event.target.value }))}
            >
              <option value="">选择候选人</option>
              {candidateOptions.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name} · {item.role}
                </option>
              ))}
            </select>
          </label>
          <label className="field-stack">
            <span>岗位</span>
            <select
              className="text-input"
              disabled={pending || disabled}
              required
              value={form.jobId}
              onChange={(event) => setForm((current) => ({ ...current, jobId: event.target.value }))}
            >
              {jobs.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.title}
                </option>
              ))}
            </select>
          </label>
          <label className="field-stack">
            <span>Offer 状态</span>
            <select
              className="text-input"
              disabled={pending || disabled}
              value={form.status}
              onChange={(event) => setForm((current) => ({ ...current, status: event.target.value }))}
            >
              <option value="Accepted">Accepted</option>
              <option value="Awaiting Response">Awaiting Response</option>
              <option value="Rejected">Rejected</option>
            </select>
          </label>
          <label className="field-stack">
            <span>薪资期望</span>
            <input
              className="text-input"
              disabled={pending || disabled}
              placeholder="45k x 15"
              value={form.salaryExpectation}
              onChange={(event) => setForm((current) => ({ ...current, salaryExpectation: event.target.value }))}
            />
          </label>
          <label className="field-stack">
            <span>入职负责人</span>
            <input
              className="text-input"
              disabled={pending || disabled}
              value={form.onboardingOwner}
              onChange={(event) => setForm((current) => ({ ...current, onboardingOwner: event.target.value }))}
            />
          </label>
          <label className="field-stack">
            <span>薪酬负责人</span>
            <input
              className="text-input"
              disabled={pending || disabled}
              value={form.payrollOwner}
              onChange={(event) => setForm((current) => ({ ...current, payrollOwner: event.target.value }))}
            />
          </label>
        </div>

        <label className="field-stack">
          <span>薪酬备注</span>
          <textarea
            className="text-area"
            disabled={pending || disabled}
            rows={3}
            value={form.compensationNotes}
            onChange={(event) => setForm((current) => ({ ...current, compensationNotes: event.target.value }))}
          />
        </label>

        <div className="form-actions">
          <button className="primary-button" disabled={pending || disabled} type="submit">
            {disabled ? "启动 API 后可用" : pending ? "创建中..." : "创建 Offer 交接"}
          </button>
          <p className="subtle-text">创建后会同步岗位 Offer 计数、候选人状态和时间线。</p>
        </div>
      </form>

      {error ? <div className="error-banner">Offer 操作失败：{error}</div> : null}
      {success ? <div className="success-banner">{success}</div> : null}
    </div>
  );
}
