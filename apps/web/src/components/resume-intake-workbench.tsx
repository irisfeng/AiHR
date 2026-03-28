"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { browserApiBaseUrl, type ResumeIntakeJobRecord } from "@/lib/api";
import type { JobRecord } from "@/lib/site-data";

function intakeStatusTone(status: string): "positive" | "critical" | "accent" | "neutral" {
  if (status === "Completed" || status === "Parsed") {
    return "positive";
  }
  if (status === "Failed") {
    return "critical";
  }
  if (status === "Unsupported") {
    return "neutral";
  }
  return "accent";
}

function candidateStatusTone(status: string): "positive" | "warning" | "accent" {
  if (status.includes("推进") || status.includes("通过") || status.includes("已接受")) {
    return "positive";
  }
  if (status.includes("暂缓")) {
    return "warning";
  }
  return "accent";
}

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
  const [selectedJobId, setSelectedJobId] = useState(recentJobs[0]?.id ?? "");
  const [detailPending, setDetailPending] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const displayJobs = useMemo(() => {
    const seen = new Set<string>();
    return [trackedJob, ...recentJobs].filter((item): item is ResumeIntakeJobRecord => {
      if (!item || seen.has(item.id)) {
        return false;
      }
      seen.add(item.id);
      return true;
    });
  }, [recentJobs, trackedJob]);

  const activeJob = trackedJob?.id === selectedJobId ? trackedJob : null;

  useEffect(() => {
    if (!selectedJobId && recentJobs[0]?.id) {
      setSelectedJobId(recentJobs[0].id);
    }
  }, [recentJobs, selectedJobId]);

  useEffect(() => {
    if (disabled || !selectedJobId || trackedJob?.id === selectedJobId) {
      return;
    }

    let cancelled = false;

    async function loadJobDetail() {
      setDetailPending(true);
      try {
        const response = await fetch(`${browserApiBaseUrl}/api/intake-jobs/${selectedJobId}`, {
          cache: "no-store",
        });
        if (!response.ok) {
          throw new Error(`API ${response.status}`);
        }
        const payload = (await response.json()) as ResumeIntakeJobRecord;
        if (!cancelled) {
          setTrackedJob(payload);
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "加载导入结果失败");
        }
      } finally {
        if (!cancelled) {
          setDetailPending(false);
        }
      }
    }

    void loadJobDetail();

    return () => {
      cancelled = true;
    };
  }, [disabled, selectedJobId, trackedJob?.id]);

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
      setSelectedJobId(payload.id);
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
            <span className={`status-pill status-pill--${intakeStatusTone(trackedJob.status)}`}>
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
        {selectedJobId ? (
          activeJob ? (
            <article className="result-card">
              <div className="compact-card__top">
                <div>
                  <h4>
                    导入审阅 · {activeJob.archiveName}
                  </h4>
                  <p className="subtle-text">
                    {activeJob.jobTitle} · 负责人 {activeJob.owner}
                  </p>
                </div>
                <span className={`status-pill status-pill--${intakeStatusTone(activeJob.status)}`}>
                  {activeJob.status}
                </span>
              </div>
              <div className="metric-inline">
                <span>解析 {activeJob.summary.parsedCount}</span>
                <span>不支持 {activeJob.summary.unsupportedCount}</span>
                <span>失败 {activeJob.summary.failedCount}</span>
                <span>入库 {activeJob.summary.createdCandidateCount}</span>
              </div>

              {activeJob.items.length ? (
                <div className="stack-list" style={{ marginTop: 14 }}>
                  {activeJob.items.map((item) =>
                    item.candidateSummary ? (
                      <article className="candidate-card" key={item.id}>
                        <div className="compact-card__top">
                          <div>
                            <h4>{item.candidateSummary.name}</h4>
                            <p className="subtle-text">
                              {item.fileName} · {item.parserEngine || "待识别"} · 候选人 {item.candidateId}
                            </p>
                          </div>
                          <span className={`status-pill status-pill--${candidateStatusTone(item.candidateSummary.status)}`}>
                            {item.candidateSummary.status}
                          </span>
                        </div>
                        <div className="candidate-card__footer">
                          <div className="metric-inline">
                            <span>{item.candidateSummary.role}</span>
                            <span>{item.candidateSummary.city}</span>
                            <span>{item.candidateSummary.source}</span>
                          </div>
                          <div className="score-badge">{item.candidateSummary.score}</div>
                        </div>
                        <div className="candidate-card__body">
                          <div>
                            <p className="eyebrow">高亮证据</p>
                            <ul className="bullet-list">
                              {item.candidateSummary.highlights.map((highlight) => (
                                <li key={highlight}>{highlight}</li>
                              ))}
                            </ul>
                          </div>
                          <div>
                            <p className="eyebrow">待确认风险</p>
                            <ul className="bullet-list bullet-list--soft">
                              {item.candidateSummary.risks.map((risk) => (
                                <li key={risk}>{risk}</li>
                              ))}
                            </ul>
                          </div>
                        </div>
                        <div className="candidate-card__footer">
                          <small>
                            解析状态 {item.status}
                            {item.reason ? ` · ${item.reason}` : ""}
                          </small>
                          <div className="action-chip">{item.candidateSummary.nextAction}</div>
                        </div>
                      </article>
                    ) : (
                      <article className="mini-stat" key={item.id}>
                        <strong>
                          {item.fileName} · {item.status}
                        </strong>
                        <span>
                          {item.parserEngine || "待识别"}
                          {item.reason ? ` · ${item.reason}` : ""}
                        </span>
                      </article>
                    ),
                  )}
                </div>
              ) : (
                <p className="subtle-text" style={{ marginTop: 14 }}>
                  这个导入作业还没有可审阅的明细。后台完成解析后会自动补齐候选人摘要。
                </p>
              )}
            </article>
          ) : detailPending ? (
            <p className="subtle-text">正在加载导入结果...</p>
          ) : null
        ) : null}
      </div>

      <div className="stack-list">
        {displayJobs.length ? (
          displayJobs.map((job) => (
            <button
              className={`note-card note-card--interactive${selectedJobId === job.id ? " note-card--active" : ""}`}
              key={job.id}
              type="button"
              onClick={() => {
                setSelectedJobId(job.id);
                setError("");
                setSuccess("");
              }}
            >
              <div className="compact-card__top">
                <h4>
                  {job.archiveName} · {job.jobTitle}
                </h4>
                <span className={`status-pill status-pill--${intakeStatusTone(job.status)}`}>{job.status}</span>
              </div>
              <p>
                解析 {job.summary.parsedCount}/{job.summary.totalFiles} · 新增候选人 {job.summary.createdCandidateCount}
              </p>
              <small>
                负责人 {job.owner}
                {job.errorMessage ? ` · ${job.errorMessage}` : ""}
              </small>
            </button>
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
