"use client";

import { useMemo, useState } from "react";

import { StatusPill } from "@/components/chrome";
import { getCandidateExportDownloadUrl } from "@/lib/api";
import type { CandidateExportRow } from "@/lib/site-data";

function finalStatusTone(status: string): "positive" | "warning" | "accent" | "neutral" {
  if (status === "已录用") {
    return "positive";
  }
  if (status === "未录用") {
    return "neutral";
  }
  if (status.includes("待") || status.includes("中")) {
    return "warning";
  }
  return "accent";
}

export function CandidateExportPanel(props: {
  rows: CandidateExportRow[];
  disabled?: boolean;
}) {
  const { rows, disabled = false } = props;
  const [keyword, setKeyword] = useState("");
  const [agency, setAgency] = useState("全部");
  const [finalStatus, setFinalStatus] = useState("全部");

  const agencies = useMemo(
    () => ["全部", ...Array.from(new Set(rows.map((item) => item.agency).filter(Boolean))).sort((left, right) => left.localeCompare(right))],
    [rows],
  );

  const filteredRows = useMemo(() => {
    return rows.filter((row) => {
      const matchKeyword =
        !keyword ||
        [row.name, row.jobTitle, row.agency, row.currentStatus, row.remarks]
          .join(" ")
          .toLowerCase()
          .includes(keyword.toLowerCase());
      const matchAgency = agency === "全部" || row.agency === agency;
      const matchFinalStatus = finalStatus === "全部" || row.finalStatus === finalStatus;
      return matchKeyword && matchAgency && matchFinalStatus;
    });
  }, [agency, finalStatus, keyword, rows]);

  const summary = useMemo(() => {
    const hired = rows.filter((row) => row.finalStatus === "已录用").length;
    const rejected = rows.filter((row) => row.finalStatus === "未录用").length;
    return {
      total: rows.length,
      hired,
      rejected,
      inProgress: rows.length - hired - rejected,
    };
  }, [rows]);

  function handleDownload() {
    if (disabled) {
      return;
    }
    window.location.href = getCandidateExportDownloadUrl();
  }

  return (
    <div className="stack-list">
      <div className="export-summary-grid">
        <article className="mini-stat">
          <strong>{summary.total}</strong>
          <span>总候选人数</span>
        </article>
        <article className="mini-stat">
          <strong>{summary.hired}</strong>
          <span>已录用</span>
        </article>
        <article className="mini-stat">
          <strong>{summary.rejected}</strong>
          <span>未录用</span>
        </article>
        <article className="mini-stat">
          <strong>{summary.inProgress}</strong>
          <span>推进中</span>
        </article>
      </div>

      <div className="field-grid">
        <label className="field-stack">
          <span>搜索</span>
          <input
            className="text-input"
            placeholder="按姓名、岗位、备注搜索"
            value={keyword}
            onChange={(event) => setKeyword(event.target.value)}
          />
        </label>
        <label className="field-stack">
          <span>代理商</span>
          <select className="text-input" value={agency} onChange={(event) => setAgency(event.target.value)}>
            {agencies.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="field-grid">
        <label className="field-stack">
          <span>最终去向</span>
          <select className="text-input" value={finalStatus} onChange={(event) => setFinalStatus(event.target.value)}>
            {["全部", "已录用", "未录用", "待经理复核", "面试中", "待录用收口"].map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
        <label className="field-stack">
          <span>导出</span>
          <button className="secondary-button export-button" disabled={disabled} onClick={handleDownload} type="button">
            {disabled ? "启动 API 后可下载" : "下载候选人总表"}
          </button>
        </label>
      </div>

      <div className="stack-list">
        {filteredRows.length ? (
          filteredRows.slice(0, 8).map((row) => (
            <article className="list-card" key={row.candidateId}>
              <div className="list-card__headline">
                <div>
                  <h4>
                    {row.name} · {row.jobTitle}
                  </h4>
                  <p className="subtle-text">
                    {row.agency || row.source} · 收到时间 {row.receivedAt}
                  </p>
                </div>
                <StatusPill tone={finalStatusTone(row.finalStatus)}>{row.finalStatus}</StatusPill>
              </div>
              <p className="list-card__body">{row.remarks || row.currentStatus}</p>
              <div className="metric-inline">
                <span>AI 初筛 {row.aiScreeningResult}</span>
                <span>经理复核 {row.managerReviewResult || "待处理"}</span>
                <span>面试 {row.interviewStages || "未开始"}</span>
                <span>薪酬 {row.salaryResult || "待确认"}</span>
              </div>
            </article>
          ))
        ) : (
          <p className="subtle-text">当前筛选条件下没有候选人记录。</p>
        )}
      </div>
    </div>
  );
}
