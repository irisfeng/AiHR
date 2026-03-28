"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { createRequisitionIntake, generateRequisitionJd } from "@/lib/api";
import type { RequisitionIntakeRecord } from "@/lib/site-data";

export function RequisitionIntakeWorkbench(props: {
  requisitions: RequisitionIntakeRecord[];
  disabled?: boolean;
}) {
  const { requisitions, disabled = false } = props;
  const router = useRouter();
  const [rawRequestText, setRawRequestText] = useState("");
  const [owner, setOwner] = useState("周岩");
  const [hiringManager, setHiringManager] = useState("张经理");
  const [selectedId, setSelectedId] = useState(requisitions[0]?.id ?? "");
  const [localRecord, setLocalRecord] = useState<RequisitionIntakeRecord | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const records = useMemo(() => {
    const merged = localRecord ? [localRecord, ...requisitions.filter((item) => item.id !== localRecord.id)] : requisitions;
    return merged;
  }, [localRecord, requisitions]);
  const selected = records.find((item) => item.id === selectedId) ?? records[0] ?? null;
  const extractedFields = useMemo(
    () => (selected ? Object.entries(selected.extractedPayload).map(([key, value]) => ({ key, value: String(value || "").trim() })) : []),
    [selected],
  );

  async function handleCreate(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError("");
    setSuccess("");
    try {
      const created = await createRequisitionIntake({
        owner,
        hiring_manager: hiringManager,
        raw_request_text: rawRequestText,
      });
      setLocalRecord(created);
      setSelectedId(created.id);
      setRawRequestText("");
      setSuccess("已生成岗位需求单初稿。");
      router.refresh();
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "创建失败");
    } finally {
      setPending(false);
    }
  }

  async function handleGenerateJd() {
    if (!selected) {
      return;
    }
    setPending(true);
    setError("");
    setSuccess("");
    try {
      const updated = await generateRequisitionJd(selected.id);
      setLocalRecord(updated);
      setSelectedId(updated.id);
      setSuccess("已生成 JD 并推到待发代理。");
      router.refresh();
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "生成 JD 失败");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="stack-list">
      <form className="workbench-form" onSubmit={handleCreate}>
        <div className="field-grid">
          <label className="field-stack">
            <span>HR 负责人</span>
            <input className="text-input" disabled={pending || disabled} value={owner} onChange={(event) => setOwner(event.target.value)} />
          </label>
          <label className="field-stack">
            <span>用人经理</span>
            <input
              className="text-input"
              disabled={pending || disabled}
              value={hiringManager}
              onChange={(event) => setHiringManager(event.target.value)}
            />
          </label>
        </div>

        <label className="field-stack">
          <span>经理原始文本</span>
          <textarea
            className="text-area"
            disabled={pending || disabled}
            rows={6}
            placeholder="把经理在微信/飞书里发来的原始需求直接贴进来。"
            value={rawRequestText}
            onChange={(event) => setRawRequestText(event.target.value)}
          />
        </label>

        <div className="form-actions">
          <button className="primary-button" disabled={pending || disabled} type="submit">
            {disabled ? "启动 API 后可用" : pending ? "创建中..." : "生成岗位需求单初稿"}
          </button>
          <p className="subtle-text">系统会先抽字段，再由 HR 补齐缺失项，不要求经理写标准 JD。</p>
        </div>
      </form>

      <div className="split-workbench" id="requisition-intake">
        <div className="stack-list">
          {records.length ? (
            records.map((item) => (
              <button
                className={`note-card note-card--interactive${selected?.id === item.id ? " note-card--active" : ""}`}
                key={item.id}
                type="button"
                onClick={() => setSelectedId(item.id)}
              >
                <div className="compact-card__top">
                  <h4>{item.extractedPayload["岗位名称"] || "待确认岗位"}</h4>
                  <span className="status-pill status-pill--accent">{item.status}</span>
                </div>
                <p>{item.rawRequestText}</p>
                <small>{item.hiringManager}</small>
              </button>
            ))
          ) : (
            <p className="subtle-text">当前还没有岗位需求单。</p>
          )}
        </div>

        <article className="result-card" id="jd-confirmation">
          {selected ? (
            <>
              <div className="compact-card__top">
                <div>
                  <h4>{selected.extractedPayload["岗位名称"] || "待确认岗位"}</h4>
                  <p className="subtle-text">用人经理：{selected.hiringManager}</p>
                </div>
                <span className="status-pill status-pill--warning">{selected.status}</span>
              </div>
              <div className="field-grid">
                {extractedFields.map((field) => (
                  <div className="mini-stat" key={field.key}>
                    <strong>{field.key}</strong>
                    <span>{field.value || "待确认"}</span>
                  </div>
                ))}
              </div>
              {selected.missingFields.length ? (
                <div className="error-banner">缺失信息：{selected.missingFields.join("、")}</div>
              ) : null}
              {selected.jdText ? <pre className="result-pre">{selected.jdText}</pre> : <p className="subtle-text">还未生成 JD。</p>}
              <div className="form-actions">
                <button className="secondary-button" disabled={pending || disabled || !selected} onClick={() => void handleGenerateJd()} type="button">
                  {pending ? "生成中..." : "生成 JD"}
                </button>
                <p className="subtle-text">生成后会自动创建或更新岗位，并推到待发代理。</p>
              </div>
            </>
          ) : (
            <p className="subtle-text">选择一条岗位需求单后，这里会显示系统整理出的结构化字段和 JD 草稿。</p>
          )}
        </article>
      </div>

      {error ? <div className="error-banner">{error}</div> : null}
      {success ? <div className="success-banner">{success}</div> : null}
    </div>
  );
}
