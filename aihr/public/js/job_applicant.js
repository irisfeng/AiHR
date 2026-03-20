frappe.ui.form.on("Job Applicant", {
  refresh(frm) {
    addApplicantActions(frm);
    renderApplicantSnapshot(frm);
  },
});

function addApplicantActions(frm) {
  if (frm.is_new()) {
    return;
  }

  frm.add_custom_button("运行 AI 初筛", async () => {
    await frappe.call({
      method: "aihr.api.recruitment.screen_job_applicant",
      args: { job_applicant: frm.doc.name, save: 1 },
      freeze: true,
      freeze_message: "正在生成候选人摘要卡...",
    });
    await frm.reload_doc();
    frappe.show_alert({ message: "AI 初筛已更新", indicator: "green" });
  });
}

async function renderApplicantSnapshot(frm) {
  const field = frm.get_field("aihr_summary_card_html");
  if (!field) {
    return;
  }

  if (frm.is_new()) {
    field.$wrapper.html(renderEmptyCard("保存候选人后，系统会自动生成 AI 摘要卡。"));
    return;
  }

  const response = await frappe.call({
    method: "aihr.api.recruitment.get_job_applicant_snapshot",
    args: { job_applicant: frm.doc.name },
  });

  const data = response.message || {};
  const applicant = data.job_applicant || {};
  const screening = data.screening;
  const opening = data.job_opening || {};
  const requisition = data.job_requisition || {};

  if (!screening) {
    field.$wrapper.html(renderEmptyCard("当前还没有 AI Screening。点击“运行 AI 初筛”即可生成。"));
    return;
  }

  field.$wrapper.html(`
    <div style="border: 1px solid var(--border-color); border-radius: 14px; padding: 16px; background: #fff;">
      <div style="display: flex; justify-content: space-between; gap: 12px; align-items: center; margin-bottom: 12px;">
        <div>
          <div style="font-size: 15px; font-weight: 700;">${escapeHtml(applicant.applicant_name || frm.doc.applicant_name || "候选人")}</div>
          <div style="font-size: 12px; color: var(--text-muted); margin-top: 4px;">
            ${escapeHtml(opening.job_title || "未关联岗位")}
          </div>
        </div>
        <div style="text-align: right;">
          <div style="display: inline-block; padding: 4px 10px; border-radius: 999px; background: #eef6ff; color: #1658b7; font-size: 12px; font-weight: 600;">
            ${escapeHtml(statusLabel(screening.status || "Ready for Review"))}
          </div>
          <div style="font-size: 22px; font-weight: 700; margin-top: 6px;">${formatScore(screening.overall_score)}</div>
        </div>
      </div>

      <div style="display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; margin-bottom: 14px;">
        ${metricCard("候选人城市", applicant.aihr_candidate_city || "未提取")}
        ${metricCard("工作年限", formatYears(applicant.aihr_years_experience))}
        ${metricCard("下一步动作", applicant.aihr_next_action || "待确认")}
      </div>

      <div style="margin-bottom: 14px;">
        <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 6px;">AI 摘要</div>
        <div style="line-height: 1.6;">${escapeHtml(screening.ai_summary || "暂无摘要")}</div>
      </div>

      <div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin-bottom: 14px;">
        ${listBlock("匹配技能", screening.matched_skills)}
        ${listBlock("缺失技能", screening.missing_skills)}
      </div>

      <div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin-bottom: 14px;">
        ${listBlock("优势", screening.strengths)}
        ${listBlock("风险点", screening.risks)}
      </div>

      ${listBlock("建议追问问题", screening.suggested_questions, true)}

      <div style="margin-top: 14px; font-size: 12px; color: var(--text-muted);">
        目标城市：${escapeHtml(requisition.aihr_work_city || "未设置")}
      </div>
    </div>
  `);
}

function metricCard(label, value) {
  return `
    <div style="border-radius: 12px; padding: 12px; background: #f8fafc;">
      <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 4px;">${escapeHtml(label)}</div>
      <div style="font-size: 14px; font-weight: 600;">${escapeHtml(value)}</div>
    </div>
  `;
}

function listBlock(title, items, fullWidth) {
  const listItems = (items || []).length
    ? (items || []).map((item) => `<li style="margin-bottom: 4px;">${escapeHtml(item)}</li>`).join("")
    : `<li style="margin-bottom: 4px;">暂无</li>`;
  const widthStyle = fullWidth ? "grid-column: 1 / -1;" : "";

  return `
    <div style="border-radius: 12px; padding: 12px; background: #f8fafc; ${widthStyle}">
      <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 6px;">${escapeHtml(title)}</div>
      <ul style="padding-left: 18px; margin: 0;">${listItems}</ul>
    </div>
  `;
}

function renderEmptyCard(message) {
  return `
    <div style="border: 1px dashed var(--border-color); border-radius: 14px; padding: 18px; background: #fff; color: var(--text-muted);">
      ${escapeHtml(message)}
    </div>
  `;
}

function formatScore(value) {
  if (value === null || value === undefined || value === "") {
    return "--";
  }
  return `${Number(value).toFixed(0)} / 100`;
}

function formatYears(value) {
  if (!value) {
    return "未提取";
  }
  return `${value} 年`;
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
    Advance: "建议推进",
    "Ready for Review": "待经理复核",
    Hold: "建议暂缓",
    Reject: "建议淘汰",
    Screened: "已初筛",
    "Not Screened": "未初筛",
    "Manager Review": "经理评估中",
    Interview: "面试中",
    Offer: "待发 Offer",
    Hired: "已录用",
  };

  return labels[value] || value || "待确认";
}
