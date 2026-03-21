frappe.ui.form.on("Job Offer", {
  async refresh(frm) {
    await renderOfferSnapshot(frm);

    if (frm.is_new()) {
      return;
    }

    frm.add_custom_button("准备入职交接", async () => {
      await frappe.call({
        method: "aihr.api.recruitment.prepare_job_offer_handoff",
        args: { job_offer: frm.doc.name, save: 1 },
        freeze: true,
        freeze_message: "正在准备 Offer 交接信息...",
      });
      await frm.reload_doc();
      await renderOfferSnapshot(frm);
      frappe.show_alert({ message: "Offer 交接信息已准备", indicator: "green" });
    });

    frm.add_custom_button("标记薪酬交接就绪", async () => {
      await frappe.call({
        method: "aihr.api.recruitment.mark_job_offer_payroll_ready",
        args: { job_offer: frm.doc.name, save: 1 },
        freeze: true,
        freeze_message: "正在同步薪酬交接状态...",
      });
      await frm.reload_doc();
      await renderOfferSnapshot(frm);
      frappe.show_alert({ message: "薪酬交接状态已更新", indicator: "green" });
    });

    if (frm.doc.status === "Accepted") {
      frm.add_custom_button("创建入职交接", async () => {
        const response = await frappe.call({
          method: "aihr.api.recruitment.create_employee_onboarding_from_offer",
          args: { job_offer: frm.doc.name, save: 1 },
          freeze: true,
          freeze_message: "正在创建入职交接...",
        });
        const result = response.message || {};
        if (result.route) {
          frappe.set_route("Form", "Employee Onboarding", result.employee_onboarding);
        }
      });
    }

    if (frm.doc.job_applicant) {
      frm.add_custom_button("查看候选人摘要", () => {
        frappe.set_route("Form", "Job Applicant", frm.doc.job_applicant);
      });
    }
  },
});

async function renderOfferSnapshot(frm) {
  const field = frm.get_field("aihr_offer_snapshot_html");
  if (!field) {
    return;
  }

  if (frm.is_new()) {
    field.$wrapper.html(renderOfferEmpty("先保存 Offer，再生成 AIHR Offer 交接面板。"));
    return;
  }

  const response = await frappe.call({
    method: "aihr.api.recruitment.get_job_offer_snapshot",
    args: { job_offer: frm.doc.name },
  });

  const data = response.message || {};
  const offer = data.job_offer || {};
  const applicant = data.job_applicant || {};
  const opening = data.job_opening || {};
  const screening = data.screening || null;
  const actions = data.actions || {};

  field.$wrapper.html(`
    <div style="border-radius: 18px; padding: 20px; background: radial-gradient(circle at top left, #fff7ed, #ffffff 48%, #eff6ff 100%); border: 1px solid rgba(249, 115, 22, 0.12); overflow: hidden;">
      <div style="display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; margin-bottom: 18px; flex-wrap: wrap;">
        <div style="max-width: 58%;">
          <div style="font-size: 12px; letter-spacing: 0.08em; text-transform: uppercase; color: #c2410c; font-weight: 700;">AIHR Offer Handoff</div>
          <div style="font-size: 28px; font-weight: 700; margin-top: 6px; color: #0f172a;">${escapeHtml(applicant.applicant_name || frm.doc.applicant_name || "Offer 交接")}</div>
          <div style="margin-top: 8px; color: var(--text-muted); line-height: 1.7;">
            ${escapeHtml(opening.job_title || offer.designation || "未关联岗位")} · ${escapeHtml(offer.company || "公司待补充")}
          </div>
        </div>
        <div style="min-width: 280px; border-radius: 16px; padding: 16px; background: linear-gradient(135deg, #0f766e, #115e59); color: #fff;">
          <div style="font-size: 12px; color: rgba(255,255,255,0.76);">当前推进建议</div>
          <div style="margin-top: 10px; font-size: 15px; font-weight: 700; line-height: 1.7;">${escapeHtml(actions.next_action || "确认 Offer 反馈与入职交接")}</div>
          <div style="margin-top: 10px; font-size: 12px; color: rgba(255,255,255,0.76);">Offer 不是终点，关键是把候选人状态、入职动作和薪酬建档衔接起来。</div>
        </div>
      </div>

      <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 18px;">
        ${chip(statusLabel(offer.status), "#fff7ed", "#c2410c")}
        ${chip(payrollLabel(offer.payroll_handoff_status), "#eff6ff", "#1d4ed8")}
        ${chip(offer.onboarding_owner || "待分配入职负责人", "#ecfdf5", "#047857")}
        ${chip(offer.offer_date || "Offer 日期待补充", "#f8fafc", "#475569")}
      </div>

      <div style="display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-bottom: 18px;">
        ${metricCard("候选人期望", applicant.salary_expectation || "待补充")}
        ${metricCard("匹配分", formatScore(applicant.aihr_match_score))}
        ${metricCard("薪酬交接", payrollLabel(offer.payroll_handoff_status))}
        ${metricCard("入职负责人", offer.onboarding_owner || "待分配")}
      </div>

      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
        <div style="display: grid; gap: 14px;">
          <div style="border-radius: 16px; padding: 16px; background: #ffffff; border: 1px solid rgba(15, 23, 42, 0.08);">
            <div style="font-size: 13px; color: var(--text-muted); margin-bottom: 10px;">交接摘要</div>
            <div style="font-size: 13px; line-height: 1.8; color: #0f172a; white-space: pre-wrap;">${escapeHtml(actions.handoff_summary || "待生成 Offer 交接摘要。")}</div>
          </div>
          <div style="border-radius: 16px; padding: 16px; background: #ffffff; border: 1px solid rgba(15, 23, 42, 0.08);">
            <div style="font-size: 13px; color: var(--text-muted); margin-bottom: 10px;">薪酬与条款备注</div>
            <div style="font-size: 14px; line-height: 1.8; color: #0f172a;">${escapeHtml(offer.compensation_notes || "待确认薪资结构、试用期和补贴项。")}</div>
            <div style="margin-top: 10px; font-size: 12px; color: var(--text-muted); line-height: 1.7;">${escapeHtml(offer.terms_preview || "Offer 条款内容会在这里显示摘要。")}</div>
          </div>
        </div>
        <div style="display: grid; gap: 14px;">
          <div style="border-radius: 16px; padding: 16px; background: linear-gradient(135deg, #0f172a, #1e293b); color: #fff;">
            <div style="font-size: 13px; color: rgba(255,255,255,0.72); margin-bottom: 10px;">候选人摘要</div>
            <div style="font-size: 13px; line-height: 1.8; color: rgba(255,255,255,0.92);">${escapeHtml((screening && screening.ai_summary) || "暂无 AI 摘要，可返回候选人页查看或补跑 AI 初筛。")}</div>
          </div>
          <div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px;">
            ${listBlock("优势", screening ? screening.strengths : [])}
            ${listBlock("风险点", screening ? screening.risks : [])}
          </div>
        </div>
      </div>
    </div>
  `);
}

function metricCard(label, value) {
  return `
    <div style="border-radius: 14px; padding: 14px; background: #ffffff; border: 1px solid rgba(15, 23, 42, 0.08); box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);">
      <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 6px;">${escapeHtml(label)}</div>
      <div style="font-size: 15px; font-weight: 700; line-height: 1.6;">${escapeHtml(value)}</div>
    </div>
  `;
}

function listBlock(title, items) {
  const listItems = (items || []).length
    ? (items || []).map((item) => `<li style="margin-bottom: 4px;">${escapeHtml(item)}</li>`).join("")
    : "<li style=\"margin-bottom: 4px;\">暂无</li>";

  return `
    <div style="border-radius: 14px; padding: 14px; background: #ffffff; border: 1px solid rgba(15, 23, 42, 0.08);">
      <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 8px;">${escapeHtml(title)}</div>
      <ul style="padding-left: 18px; margin: 0; line-height: 1.7;">${listItems}</ul>
    </div>
  `;
}

function chip(value, background, color) {
  return `
    <span style="display: inline-flex; align-items: center; padding: 6px 10px; border-radius: 999px; font-size: 12px; font-weight: 700; background: ${background}; color: ${color};">
      ${escapeHtml(value)}
    </span>
  `;
}

function formatScore(value) {
  if (value === null || value === undefined || value === "" || Number.isNaN(Number(value))) {
    return "--";
  }
  return `${Number(value).toFixed(0)} 分`;
}

function payrollLabel(value) {
  const labels = {
    "Not Started": "待准备",
    Ready: "可交接",
    Completed: "已完成",
  };

  return labels[value] || value || "待确认";
}

function statusLabel(value) {
  const labels = {
    "Awaiting Response": "待候选人确认",
    Accepted: "已接受",
    Rejected: "已拒绝",
  };

  return labels[value] || value || "待确认";
}

function renderOfferEmpty(message) {
  return `
    <div style="border: 1px dashed var(--border-color); border-radius: 14px; padding: 18px; color: var(--text-muted); background: #fff;">
      ${escapeHtml(message)}
    </div>
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
