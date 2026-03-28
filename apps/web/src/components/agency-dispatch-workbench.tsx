"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { StatusPill, TagList } from "@/components/chrome";
import { createAgencyDispatch, type AgencyDispatchRecord } from "@/lib/api";
import type { JobRecord } from "@/lib/site-data";

function dispatchTone(status: string): "positive" | "warning" | "accent" | "neutral" {
  if (status.includes("回简历") || status.includes("已回")) {
    return "positive";
  }
  if (status.includes("待")) {
    return "warning";
  }
  if (status.includes("发送")) {
    return "accent";
  }
  return "neutral";
}

export function AgencyDispatchWorkbench(props: {
  jobs: JobRecord[];
  dispatches: AgencyDispatchRecord[];
  disabled?: boolean;
}) {
  const { jobs, dispatches, disabled = false } = props;
  const router = useRouter();
  const jobsById = useMemo(() => new Map(jobs.map((item) => [item.id, item])), [jobs]);
  const [localDispatch, setLocalDispatch] = useState<AgencyDispatchRecord | null>(null);
  const [form, setForm] = useState({
    jobId: jobs[0]?.id ?? "",
    agencyName: "",
    sentAtLabel: "03-28 14:30",
    notes: "",
  });
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const records = useMemo(() => {
    const seen = new Set<string>();
    return [localDispatch, ...dispatches].filter((item): item is AgencyDispatchRecord => {
      if (!item || seen.has(item.id)) {
        return false;
      }
      seen.add(item.id);
      return true;
    });
  }, [dispatches, localDispatch]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError("");
    setSuccess("");

    try {
      const created = await createAgencyDispatch({
        job_id: form.jobId,
        agency_name: form.agencyName,
        sent_at_label: form.sentAtLabel,
        notes: form.notes,
      });
      setLocalDispatch(created);
      setSuccess(`已记录 ${created.agencyName} 的外发动作。`);
      setForm((current) => ({
        ...current,
        agencyName: "",
        notes: "",
      }));
      router.refresh();
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "记录外发失败");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="split-workbench">
      <div className="stack-list">
        {records.length ? (
          records.map((dispatch) => {
            const job = jobsById.get(dispatch.jobId);
            return (
              <article className="note-card" key={dispatch.id}>
                <div className="compact-card__top">
                  <div>
                    <h4>{dispatch.agencyName}</h4>
                    <p className="subtle-text">{job?.title ?? dispatch.jobId}</p>
                  </div>
                  <StatusPill tone={dispatchTone(dispatch.dispatchStatus)}>{dispatch.dispatchStatus}</StatusPill>
                </div>
                <p>
                  已发送时间：{dispatch.sentAtLabel}
                  {dispatch.firstResumeAtLabel ? ` · 首份简历：${dispatch.firstResumeAtLabel}` : ""}
                </p>
                {job ? <TagList items={job.skills.slice(0, 5)} /> : null}
                {dispatch.notes ? <small>{dispatch.notes}</small> : null}
              </article>
            );
          })
        ) : (
          <p className="subtle-text">当前还没有代理外发记录。生成 JD 后在右侧登记发送对象。</p>
        )}
      </div>

      <form className="workbench-form" onSubmit={handleSubmit}>
        <div className="field-grid">
          <label className="field-stack">
            <span>关联岗位</span>
            <select
              className="text-input"
              disabled={pending || disabled || !jobs.length}
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
            <span>代理商</span>
            <input
              className="text-input"
              disabled={pending || disabled}
              placeholder="例如：锐仕方达"
              required
              value={form.agencyName}
              onChange={(event) => setForm((current) => ({ ...current, agencyName: event.target.value }))}
            />
          </label>
        </div>

        <label className="field-stack">
          <span>发送时间</span>
          <input
            className="text-input"
            disabled={pending || disabled}
            value={form.sentAtLabel}
            onChange={(event) => setForm((current) => ({ ...current, sentAtLabel: event.target.value }))}
          />
        </label>

        <label className="field-stack">
          <span>外发备注</span>
          <textarea
            className="text-area"
            disabled={pending || disabled}
            placeholder="例如：优先看 Python 微服务背景，本周内给首批简历。"
            rows={4}
            value={form.notes}
            onChange={(event) => setForm((current) => ({ ...current, notes: event.target.value }))}
          />
        </label>

        <div className="form-actions">
          <button className="primary-button" disabled={pending || disabled || !jobs.length} type="submit">
            {disabled ? "启动 API 后可用" : pending ? "记录中..." : "记录已发代理"}
          </button>
          <p className="subtle-text">外发后岗位会自动进入“代理寻访中”，减少 Excel 手工记账。</p>
        </div>

        {error ? <div className="error-banner">{error}</div> : null}
        {success ? <div className="success-banner">{success}</div> : null}
      </form>
    </div>
  );
}
