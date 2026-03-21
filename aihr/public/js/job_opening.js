frappe.ui.form.on("Job Opening", {
  async refresh(frm) {
    await renderOpeningSnapshot(frm);

    if (frm.is_new()) {
      return;
    }

    if (frm.doc.job_requisition) {
      frm.add_custom_button("同步代理发布包", async () => {
        await frappe.call({
          method: "aihr.api.recruitment.sync_job_opening_agency_pack",
          args: { job_opening: frm.doc.name, save: 1 },
          freeze: true,
          freeze_message: "正在同步岗位发布包...",
        });
        await frm.reload_doc();
        await renderOpeningSnapshot(frm);
        frappe.show_alert({ message: "岗位发布包已同步", indicator: "green" });
      });
    }

    frm.add_custom_button("导入简历压缩包", () => {
      openResumeImportDialog(frm);
    });

    frm.add_custom_button("批量 AI 初筛", async () => {
      const response = await frappe.call({
        method: "aihr.api.recruitment.screen_job_opening_applicants",
        args: { job_opening: frm.doc.name, save: 1 },
        freeze: true,
        freeze_message: "正在批量生成候选人摘要卡...",
      });
      await renderOpeningSnapshot(frm);
      const result = response.message || {};
      frappe.msgprint(`已完成 ${result.screened_count || 0} 位候选人的 AI 初筛。`);
    });

    frm.add_custom_button("录入候选人", () => {
      frappe.new_doc("Job Applicant", { job_title: frm.doc.name });
    });

    frm.add_custom_button("查看候选人概览", async () => {
      const response = await frappe.call({
        method: "aihr.api.recruitment.get_job_opening_pipeline_summary",
        args: { job_opening: frm.doc.name },
      });
      const summary = response.message || {};
      const counts = summary.status_counts || {};
      const rows = Object.keys(counts).length
        ? Object.entries(counts)
            .map(([status, count]) => `<tr><td style="padding: 6px 10px;">${escapeHtml(statusLabel(status))}</td><td style="padding: 6px 10px;">${count}</td></tr>`)
            .join("")
        : `<tr><td style="padding: 6px 10px;" colspan="2">暂无候选人</td></tr>`;

      const topCandidates = (summary.top_candidates || []).length
        ? (summary.top_candidates || [])
            .map((candidate) => `<li>${escapeHtml(candidate.applicant_name || candidate.name)} / ${Number(candidate.aihr_match_score || 0).toFixed(0)} 分 / ${escapeHtml(candidate.aihr_next_action || "待确认")}</li>`)
            .join("")
        : "<li>暂无候选人</li>";

      frappe.msgprint({
        title: "候选人概览",
        message: `
          <div style="margin-bottom: 12px;">总候选人数：<b>${summary.total_applicants || 0}</b></div>
          <table style="width: 100%; border-collapse: collapse; margin-bottom: 12px;">
            <thead>
              <tr>
                <th style="text-align: left; padding: 6px 10px;">状态</th>
                <th style="text-align: left; padding: 6px 10px;">数量</th>
              </tr>
            </thead>
            <tbody>${rows}</tbody>
          </table>
          <div style="margin-bottom: 6px;"><b>Top 候选人</b></div>
          <ul style="padding-left: 18px; margin: 0;">${topCandidates}</ul>
        `,
      });
    });
  },
});

async function renderOpeningSnapshot(frm) {
  const field = frm.get_field("aihr_pipeline_summary_html");
  if (!field) {
    return;
  }

  if (frm.is_new()) {
    field.$wrapper.html(renderEmptyCard("先保存岗位，再生成 AIHR 招聘推进看板。"));
    return;
  }

  const response = await frappe.call({
    method: "aihr.api.recruitment.get_job_opening_pipeline_summary",
    args: { job_opening: frm.doc.name },
  });
  const summary = response.message || {};
  const topCandidates = summary.top_candidates || [];
  const queueText = frm.doc.aihr_next_action || "收集首批候选人并完成 AI 初筛";

  field.$wrapper.html(`
    <div style="border-radius: 18px; padding: 20px; background: linear-gradient(135deg, #0f172a, #143043 55%, #163a4b 100%); color: #fff; border: 1px solid rgba(15, 23, 42, 0.1); overflow: hidden;">
      <div style="display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; margin-bottom: 18px; flex-wrap: wrap;">
        <div style="max-width: 56%;">
          <div style="font-size: 12px; letter-spacing: 0.08em; text-transform: uppercase; color: rgba(255,255,255,0.72); font-weight: 700;">AIHR Pipeline View</div>
          <div style="font-size: 28px; font-weight: 700; margin-top: 6px;">${escapeHtml(frm.doc.job_title || frm.doc.name)}</div>
          <div style="margin-top: 8px; color: rgba(255,255,255,0.78); line-height: 1.7;">
            ${escapeHtml(frm.doc.description || "这是一条招聘中岗位记录，用于承接候选人、摘要卡和后续推进动作。")}
          </div>
        </div>
        <div style="min-width: 280px; border-radius: 16px; padding: 16px; background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.08); backdrop-filter: blur(6px);">
          <div style="font-size: 12px; color: rgba(255,255,255,0.72);">招聘推进建议</div>
          <div style="margin-top: 10px; font-size: 15px; font-weight: 700; line-height: 1.7;">${escapeHtml(queueText)}</div>
          <div style="margin-top: 10px; font-size: 12px; color: rgba(255,255,255,0.72);">建议先看右侧漏斗指标，再决定是补简历来源，还是安排经理复核。</div>
        </div>
      </div>

      <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 18px;">
        ${chip(frm.doc.status || "Open", "rgba(255,255,255,0.14)")}
        ${chip(frm.doc.aihr_posting_owner || "待分配负责人", "rgba(14,165,233,0.18)")}
        ${chip((frm.doc.aihr_channel_mix || "渠道待补充").replace(/\n/g, " / "), "rgba(249,115,22,0.2)")}
      </div>

      <div style="display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 12px; margin-bottom: 18px;">
        ${darkMetric("候选人总量", summary.total_applicants || 0)}
        ${darkMetric("待经理复核", summary.review_queue || 0)}
        ${darkMetric("建议推进", summary.advance_count || 0)}
        ${darkMetric("建议暂缓", summary.hold_count || 0)}
        ${darkMetric("最高分", formatScore(summary.top_score))}
      </div>

      <div style="display: grid; grid-template-columns: 1.2fr 0.8fr; gap: 14px;">
        <div style="border-radius: 16px; padding: 16px; background: #ffffff; color: #0f172a;">
          <div style="font-size: 13px; color: var(--text-muted); margin-bottom: 10px;">候选人优先队列</div>
          ${renderCandidateList(topCandidates)}
        </div>
        <div style="border-radius: 16px; padding: 16px; background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.08);">
          <div style="font-size: 13px; color: rgba(255,255,255,0.72); margin-bottom: 10px;">当前漏斗建议</div>
          <div style="display: grid; gap: 10px;">
            ${hintCard("AI 覆盖", `${summary.screened_count || 0} / ${summary.total_applicants || 0} 位已生成摘要卡`)}
            ${hintCard("平均匹配分", formatScore(summary.average_score))}
            ${hintCard("下一步动作", queueText)}
            ${hintCard("岗位发布包", frm.doc.aihr_agency_pack ? "已同步，可发代理/渠道" : "待同步发布包")}
          </div>
        </div>
      </div>
    </div>
  `);
}

function renderCandidateList(candidates) {
  if (!candidates.length) {
    return `
      <div style="border: 1px dashed rgba(15,23,42,0.12); border-radius: 14px; padding: 16px; color: var(--text-muted);">
        还没有候选人进入这个岗位。建议先录入候选人或导入简历，再进行批量 AI 初筛。
      </div>
    `;
  }

  return candidates
    .map(
      (candidate) => `
        <div style="display: flex; justify-content: space-between; gap: 12px; align-items: center; padding: 12px 0; border-bottom: 1px solid rgba(15,23,42,0.08);">
          <div>
            <div style="font-size: 15px; font-weight: 700;">${escapeHtml(candidate.applicant_name || candidate.name)}</div>
            <div style="font-size: 12px; color: var(--text-muted); margin-top: 4px;">
              ${escapeHtml(candidate.status_label || statusLabel(candidate.pipeline_status || candidate.status))} · ${escapeHtml(candidate.aihr_candidate_city || "城市待补充")}
            </div>
            <div style="font-size: 12px; color: var(--text-muted); margin-top: 4px;">${escapeHtml(candidate.aihr_next_action || "待确认下一步")}</div>
          </div>
          <div style="text-align: right;">
            <div style="font-size: 22px; font-weight: 700;">${formatScore(candidate.aihr_match_score)}</div>
            <a href="${escapeHtml(candidate.route || "#")}" style="display: inline-block; margin-top: 6px; color: #1d4ed8;">查看摘要卡</a>
          </div>
        </div>
      `
    )
    .join("");
}

function darkMetric(label, value) {
  return `
    <div style="border-radius: 14px; padding: 14px; background: rgba(255,255,255,0.1); backdrop-filter: blur(4px);">
      <div style="font-size: 12px; color: rgba(255,255,255,0.72); margin-bottom: 6px;">${escapeHtml(label)}</div>
      <div style="font-size: 20px; font-weight: 700;">${escapeHtml(value)}</div>
    </div>
  `;
}

function openResumeImportDialog(frm) {
  const dialog = new frappe.ui.Dialog({
    title: "导入简历压缩包",
    fields: [
      {
        fieldname: "archive_file",
        fieldtype: "Attach",
        label: "ZIP 压缩包",
        reqd: 1,
        description: "支持上传包含多份 PDF / DOCX / DOC / TXT 简历的 ZIP 文件。",
      },
      {
        fieldname: "supplier_name",
        fieldtype: "Data",
        label: "供应商名称",
      },
      {
        fieldname: "source_channel",
        fieldtype: "Data",
        label: "来源渠道",
        default: "供应商线下包",
      },
      {
        fieldname: "auto_run_screening",
        fieldtype: "Check",
        label: "导入后自动生成 AI 摘要",
        default: 1,
      },
    ],
    primary_action_label: "开始导入",
    primary_action: async (values) => {
      const response = await frappe.call({
        method: "aihr.api.recruitment.create_resume_intake_batch",
        args: {
          job_opening: frm.doc.name,
          archive_file: values.archive_file,
          supplier_name: values.supplier_name || "",
          source_channel: values.source_channel || "",
          auto_run_screening: values.auto_run_screening ? 1 : 0,
        },
        freeze: true,
        freeze_message: "正在拆分压缩包并导入候选人...",
      });

      const result = response.message || {};
      dialog.hide();
      await frm.reload_doc();
      await renderOpeningSnapshot(frm);
      frappe.msgprint({
        title: "导入完成",
        message: `
          <div style="line-height: 1.8;">
            <div>导入批次：<b>${escapeHtml(result.batch || "")}</b></div>
            <div>成功入库：<b>${Number(result.summary?.imported_count || 0)}</b></div>
            <div>跳过文件：<b>${Number(result.summary?.skipped_count || 0)}</b></div>
            <div>失败文件：<b>${Number(result.summary?.failed_count || 0)}</b></div>
            <div style="margin-top: 10px; white-space: pre-wrap; color: var(--text-muted);">${escapeHtml(result.intake_log || "暂无导入日志。")}</div>
          </div>
        `,
      });
    },
  });

  dialog.show();
}

function hintCard(label, value) {
  return `
    <div style="border-radius: 14px; padding: 12px 14px; background: rgba(255,255,255,0.08);">
      <div style="font-size: 12px; color: rgba(255,255,255,0.72); margin-bottom: 4px;">${escapeHtml(label)}</div>
      <div style="font-size: 14px; font-weight: 600; line-height: 1.6;">${escapeHtml(value)}</div>
    </div>
  `;
}

function chip(value, background) {
  return `
    <span style="display: inline-flex; align-items: center; padding: 6px 10px; border-radius: 999px; font-size: 12px; font-weight: 700; background: ${background}; color: #fff;">
      ${escapeHtml(value)}
    </span>
  `;
}

function escapeHtml(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function statusLabel(value) {
  const labels = {
    Screened: "已初筛",
    "Not Screened": "未初筛",
    "Manager Review": "经理评估中",
    Interview: "面试中",
    Rejected: "已淘汰",
    Offer: "待发 Offer",
    Hired: "已录用",
    Advance: "建议推进",
    "Ready for Review": "待经理复核",
    Hold: "建议暂缓",
  };

  return labels[value] || value || "待确认";
}

function formatScore(value) {
  if (value === null || value === undefined || value === "" || Number.isNaN(Number(value))) {
    return "--";
  }
  return `${Number(value).toFixed(0)} 分`;
}
