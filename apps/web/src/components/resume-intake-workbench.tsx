"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { browserApiBaseUrl, type ResumeIntakeJobRecord } from "@/lib/api";
import type { JobRecord } from "@/lib/site-data";

export function ResumeIntakeWorkbench(props: {
  jobs: JobRecord[];
  recentJobs: ResumeIntakeJobRecord[];
  disabled?: boolean;
}) {
  const { jobs, recentJobs, disabled = false } = props;
  const router = useRouter();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [form, setForm] = useState({
    jobId: jobs[0]?.id ?? "",
    owner: jobs[0]?.owner ?? "待分配",
    source: "ZIP 简历包",
  });
  const [trackedJob, setTrackedJob] = useState<ResumeIntakeJobRecord | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const displayJobs = useMemo(() => {
    if (!trackedJob) {
      return recentJobs;
    }
    return [trackedJob, ...recentJobs.filter((item) => item.id !== trackedJob.id)];
  }, [recentJobs, trackedJob]);

  useEffect(() => {
    if (!trackedJob || !["Queued", "Running"].includes(trackedJob.status)) {
      return;
    }

    const timer = window.setInterval(async () => {
      try {
        const response = await fetch(`${browserApiBaseUrl}/api/intake-jobs/${trackedJob.id}`, {
          cache: "no-store",
        });
        if (!response.ok) {
          throw new Error(`API ${response.status}`);
        }
        const payload = (await response.json()) as ResumeIntakeJobRecord;
        setTrackedJob(payload);
        if (payload.status === "Completed") {
          setSuccess(
            `已完成 ${payload.archiveName}，解析 ${payload.summary.parsedCount} 份，创建 ${payload.summary.createdCandidateCount} 位候选人`,
          );
          router.refresh();
        }
        if (payload.status === "Failed") {
          setError(payload.errorMessage || "导入失败");
        }
      } catch (pollError) {
        setError(pollError instanceof Error ? pollError.message : "轮询失败");
      }
    }, 800);

    return () => window.clearInterval(timer);
  }, [router, trackedJob]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedFile) {
      setError("请先选择 ZIP 简历包");
      return;
    }

    setPending(true);
    setError("");
    setSuccess("");

    try {
      const body = new FormData();
      body.append("archive", selectedFile);
      body.append("job_id", form.jobId);
      body.append("owner", form.owner);
      body.append("source", form.source);

      const response = await fetch(`${browserApiBaseUrl}/api/intake-jobs`, {
        method: "POST",
        body,
      });

      if (!response.ok) {
        throw new Error(`API ${response.status}`);
      }

      const payload = (await response.json()) as ResumeIntakeJobRecord;
      setTrackedJob(payload);
      setSuccess(`已接收 ${payload.archiveName}，后台开始解析`);
      setSelectedFile(null);
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
            <span>目标岗位</span>
            <select
              className="text-input"
              disabled={pending || disabled}
              required
              value={form.jobId}
              onChange={(event) => {
                const nextJob = jobs.find((item) => item.id === event.target.value);
                setForm((current) => ({
                  ...current,
                  jobId: event.target.value,
                  owner: nextJob?.owner ?? current.owner,
                }));
              }}
            >
              {jobs.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.title}
                </option>
              ))}
            </select>
          </label>
          <label className="field-stack">
            <span>负责人</span>
            <input
              className="text-input"
              disabled={pending || disabled}
              value={form.owner}
              onChange={(event) => setForm((current) => ({ ...current, owner: event.target.value }))}
            />
          </label>
        </div>

        <label className="field-stack">
          <span>ZIP 简历包</span>
          <input
            className="text-input"
            disabled={pending || disabled}
            accept=".zip,application/zip"
            type="file"
            onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
          />
        </label>

        <div className="form-actions">
          <button className="primary-button" disabled={pending || disabled} type="submit">
            {disabled ? "启动 API 后可用" : pending ? "上传中..." : "上传并后台解析"}
          </button>
          <p className="subtle-text">解析完成后自动写入候选人，并更新岗位漏斗。</p>
        </div>
      </form>

      {trackedJob ? (
        <article className="result-card">
          <div className="compact-card__top">
            <h4>
              {trackedJob.archiveName} · {trackedJob.jobTitle}
            </h4>
            <span className={`status-pill status-pill--${trackedJob.status === "Completed" ? "positive" : trackedJob.status === "Failed" ? "critical" : "accent"}`}>
              {trackedJob.status}
            </span>
          </div>
          <div className="metric-inline">
            <span>总文件 {trackedJob.summary.totalFiles}</span>
            <span>已解析 {trackedJob.summary.parsedCount}</span>
            <span>已入库 {trackedJob.summary.createdCandidateCount}</span>
          </div>
          {trackedJob.items.length ? (
            <div className="stack-list" style={{ marginTop: 14 }}>
              {trackedJob.items.slice(0, 4).map((item) => (
                <article className="mini-stat" key={item.id}>
                  <strong>
                    {item.fileName} · {item.status}
                  </strong>
                  <span>
                    {item.parserEngine || "待识别"}
                    {item.candidateId ? ` · 候选人 ${item.candidateId}` : ""}
                    {item.reason ? ` · ${item.reason}` : ""}
                  </span>
                </article>
              ))}
            </div>
          ) : null}
        </article>
      ) : null}

      <div className="stack-list">
        {displayJobs.length ? (
          displayJobs.map((job) => (
            <article className="note-card" key={job.id}>
              <div className="compact-card__top">
                <h4>
                  {job.archiveName} · {job.jobTitle}
                </h4>
                <span className="status-pill status-pill--neutral">{job.status}</span>
              </div>
              <p>
                解析 {job.summary.parsedCount}/{job.summary.totalFiles} · 新增候选人 {job.summary.createdCandidateCount}
              </p>
              <small>
                负责人 {job.owner}
                {job.errorMessage ? ` · ${job.errorMessage}` : ""}
              </small>
            </article>
          ))
        ) : (
          <p className="subtle-text">还没有 ZIP 导入作业，上传后这里会展示后台解析进度。</p>
        )}
      </div>

      {error ? <div className="error-banner">简历导入失败：{error}</div> : null}
      {success ? <div className="success-banner">{success}</div> : null}
    </div>
  );
}
