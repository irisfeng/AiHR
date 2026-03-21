frappe.ui.form.on("Employee Onboarding", {
  async refresh(frm) {
    await renderOnboardingSnapshot(frm);

    if (frm.is_new()) {
      return;
    }

    frm.add_custom_button("准备入职清单", async () => {
      await frappe.call({
        method: "aihr.api.recruitment.prepare_employee_onboarding",
        args: { employee_onboarding: frm.doc.name, save: 1 },
        freeze: true,
        freeze_message: "正在准备入职清单...",
      });
      await frm.reload_doc();
      await renderOnboardingSnapshot(frm);
      frappe.show_alert({ message: "入职清单已同步", indicator: "green" });
    });

    if (frm.doc.job_offer) {
      frm.add_custom_button("查看 Offer", () => {
        frappe.set_route("Form", "Job Offer", frm.doc.job_offer);
      });
    }

    if (frm.doc.job_applicant) {
      frm.add_custom_button("查看候选人摘要", () => {
        frappe.set_route("Form", "Job Applicant", frm.doc.job_applicant);
      });
    }
  },
});

async function renderOnboardingSnapshot(frm) {
  const field = frm.get_field("aihr_onboarding_snapshot_html");
  if (!field) {
    return;
  }

  if (frm.is_new()) {
    field.$wrapper.html(renderEmpty("先保存入职交接单，再生成 AIHR 入职概览。"));
    return;
  }

  const response = await frappe.call({
    method: "aihr.api.recruitment.get_employee_onboarding_snapshot",
    args: { employee_onboarding: frm.doc.name },
  });
  const data = response.message || {};
  const onboarding = data.employee_onboarding || {};
  const applicant = data.job_applicant || {};
  const offer = data.job_offer || {};
  const opening = data.job_opening || {};
  const actions = data.actions || {};

  field.$wrapper.html(`
    <div style="border-radius: 18px; padding: 20px; background: linear-gradient(135deg, #ecfeff, #ffffff 42%, #f0fdf4); border: 1px solid rgba(14, 165, 233, 0.16);">
      <div style="display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; margin-bottom: 18px; flex-wrap: wrap;">
        <div style="max-width: 58%;">
          <div style="font-size: 12px; letter-spacing: 0.08em; text-transform: uppercase; color: #0369a1; font-weight: 700;">AIHR 入职概览</div>
          <div style="font-size: 28px; font-weight: 700; margin-top: 6px; color: #0f172a;">${escapeHtml(applicant.applicant_name || "入职交接")}</div>
          <div style="margin-top: 8px; color: var(--text-muted); line-height: 1.7;">
            ${escapeHtml(opening.job_title || "未关联岗位")} · 入职日期 ${escapeHtml(onboarding.date_of_joining || "待确认")}
          </div>
        </div>
        <div style="min-width: 280px; border-radius: 16px; padding: 16px; background: #0f766e; color: #fff;">
          <div style="font-size: 12px; color: rgba(255,255,255,0.76);">当前推进建议</div>
          <div style="margin-top: 10px; font-size: 15px; font-weight: 700; line-height: 1.7;">${escapeHtml(actions.next_action || "确认入职资料与薪酬建档信息")}</div>
        </div>
      </div>

      <div style="display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-bottom: 18px;">
        ${metricCard("交接状态", statusLabel(onboarding.boarding_status))}
        ${metricCard("负责人", onboarding.handoff_owner || "待分配")}
        ${metricCard("薪酬就绪", onboarding.payroll_ready ? "已就绪" : "待准备")}
        ${metricCard("活动数", String((data.activities || []).length))}
      </div>

      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
        <div style="display: grid; gap: 14px;">
          <div style="border-radius: 16px; padding: 16px; background: #ffffff; border: 1px solid rgba(15,23,42,0.08);">
            <div style="font-size: 13px; color: var(--text-muted); margin-bottom: 10px;">交接摘要</div>
            <div style="font-size: 13px; line-height: 1.8; white-space: pre-wrap;">${escapeHtml(actions.summary || "待生成交接摘要。")}</div>
          </div>
          <div style="border-radius: 16px; padding: 16px; background: #ffffff; border: 1px solid rgba(15,23,42,0.08);">
            <div style="font-size: 13px; color: var(--text-muted); margin-bottom: 10px;">预入职说明</div>
            <div style="font-size: 14px; line-height: 1.8;">${escapeHtml(onboarding.preboarding_notes || "待补充。")}</div>
          </div>
        </div>
        <div style="display: grid; gap: 14px;">
          <div style="border-radius: 16px; padding: 16px; background: #ffffff; border: 1px solid rgba(15,23,42,0.08);">
            <div style="font-size: 13px; color: var(--text-muted); margin-bottom: 10px;">交接活动</div>
            ${renderActivityList(data.activities || [])}
          </div>
          <div style="border-radius: 16px; padding: 16px; background: #ffffff; border: 1px solid rgba(15,23,42,0.08);">
            <div style="font-size: 13px; color: var(--text-muted); margin-bottom: 10px;">Offer 关联信息</div>
            <div style="font-size: 14px; line-height: 1.8;">${escapeHtml(offer.status || "待确认")} · ${escapeHtml(offer.compensation_notes || "待补充薪酬说明")}</div>
          </div>
        </div>
      </div>
    </div>
  `);
}

function metricCard(label, value) {
  return `
    <div style="border-radius: 14px; padding: 14px; background: #ffffff; border: 1px solid rgba(15,23,42,0.08);">
      <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 6px;">${escapeHtml(label)}</div>
      <div style="font-size: 15px; font-weight: 700; line-height: 1.6;">${escapeHtml(value)}</div>
    </div>
  `;
}

function renderActivityList(items) {
  if (!items.length) {
    return `<div style="color: var(--text-muted); line-height: 1.7;">还没有活动，点击“准备入职清单”自动生成。</div>`;
  }

  return `
    <ul style="padding-left: 18px; margin: 0; line-height: 1.8;">
      ${items.map((item) => `<li style="margin-bottom: 6px;">${escapeHtml(item)}</li>`).join("")}
    </ul>
  `;
}

function statusLabel(value) {
  const labels = {
    Pending: "待启动",
    "In Process": "进行中",
    Completed: "已完成",
  };

  return labels[value] || value || "待确认";
}

function renderEmpty(message) {
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
