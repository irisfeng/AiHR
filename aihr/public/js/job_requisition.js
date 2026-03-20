frappe.ui.form.on("Job Requisition", {
  refresh(frm) {
    renderRequisitionSnapshot(frm);

    if (frm.is_new()) {
      return;
    }

    frm.add_custom_button("刷新代理发布包", async () => {
      await frappe.call({
        method: "aihr.api.recruitment.sync_job_requisition_agency_brief",
        args: { job_requisition: frm.doc.name, save: 1 },
        freeze: true,
        freeze_message: "正在刷新代理发布包...",
      });
      await frm.reload_doc();
      frappe.show_alert({ message: "代理发布包已刷新", indicator: "green" });
    });

    if (frm.doc.aihr_agency_brief) {
      frm.add_custom_button("复制代理发布包", () => {
        frappe.utils.copy_to_clipboard(frm.doc.aihr_agency_brief);
        frappe.show_alert({ message: "代理发布包已复制", indicator: "green" });
      });
    }

    frm.add_custom_button("新建招聘中岗位", () => {
      frappe.new_doc("Job Opening", {
        job_requisition: frm.doc.name,
        designation: frm.doc.designation,
        department: frm.doc.department,
      });
    });
  },
});

function renderRequisitionSnapshot(frm) {
  const field = frm.get_field("aihr_role_snapshot_html");
  if (!field) {
    return;
  }

  if (frm.is_new()) {
    field.$wrapper.html(renderRequisitionEmpty("先保存岗位需求，再生成 AIHR 岗位作战卡。"));
    return;
  }

  const salary = formatSalary(frm.doc.aihr_salary_currency, frm.doc.aihr_salary_min, frm.doc.aihr_salary_max);
  const mustHave = splitItems(frm.doc.aihr_must_have_skills);
  const niceToHave = splitItems(frm.doc.aihr_nice_to_have_skills);
  const goals = splitItems(frm.doc.reason_for_requesting || frm.doc.description);
  const nextAction = frm.doc.aihr_agency_brief
    ? "岗位信息已具备外发基础，可同步给代理或转成招聘中岗位。"
    : "先补齐岗位职责、薪资、地点和技能要求，再刷新代理发布包。";

  field.$wrapper.html(`
    <div style="border-radius: 18px; padding: 20px; background: radial-gradient(circle at top left, #effcf6, #ffffff 48%, #eef6ff); border: 1px solid #d9ece5;">
      <div style="display: flex; justify-content: space-between; gap: 14px; align-items: flex-start; margin-bottom: 16px; flex-wrap: wrap;">
        <div>
          <div style="font-size: 12px; letter-spacing: 0.08em; text-transform: uppercase; color: #0f766e; font-weight: 700;">AIHR Role Snapshot</div>
          <div style="font-size: 26px; font-weight: 700; margin-top: 6px;">${escapeHtml(frm.doc.designation || "待命名岗位")}</div>
          <div style="margin-top: 8px; color: var(--text-muted); line-height: 1.6;">
            ${escapeHtml(
              (frm.doc.description || "这是一条招聘需求记录，用于统一岗位信息、代理发布包和招聘推进动作。").slice(0, 120)
            ).replace(/\n/g, "<br>")}
          </div>
        </div>
        <div style="min-width: 240px; border-radius: 16px; padding: 14px 16px; background: rgba(15, 118, 110, 0.08);">
          <div style="font-size: 12px; color: #0f766e; font-weight: 600;">下一步建议</div>
          <div style="font-size: 15px; font-weight: 700; margin-top: 8px; line-height: 1.6;">${escapeHtml(nextAction)}</div>
        </div>
      </div>

      <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px;">
        ${pill(priorityLabel(frm.doc.aihr_priority), "#0f766e", "#e6fffb")}
        ${pill(workModeLabel(frm.doc.aihr_work_mode), "#1d4ed8", "#eff6ff")}
        ${pill(frm.doc.aihr_work_city || "城市待补充", "#7c3aed", "#f5f3ff")}
        ${pill(frm.doc.aihr_work_schedule || "班次待补充", "#ea580c", "#fff7ed")}
        ${pill(frm.doc.status || "状态待确认", "#0f172a", "#f8fafc")}
      </div>

      <div style="display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-bottom: 16px;">
        ${metricCard("薪资区间", salary)}
        ${metricCard("招聘优先级", priorityLabel(frm.doc.aihr_priority))}
        ${metricCard("工作地点", frm.doc.aihr_work_city || "待补充")}
        ${metricCard("代理发布包", frm.doc.aihr_agency_brief ? "已就绪" : "待生成")}
      </div>

      <div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px;">
        ${tagBlock("必备技能", mustHave, "#ecfeff", "#155e75")}
        ${tagBlock("加分项", niceToHave, "#fff7ed", "#9a3412")}
        ${tagBlock("招聘目标", goals, "#f8fafc", "#334155", true)}
        ${detailBlock("发布建议", nextAction, frm.doc.aihr_agency_brief ? "现在可以复制代理发布包并发给渠道。" : "刷新代理发布包后，再转入招聘中岗位。")}
      </div>
    </div>
  `);
}

function metricCard(label, value) {
  return `
    <div style="border-radius: 14px; padding: 14px; background: #ffffff; border: 1px solid rgba(15, 23, 42, 0.08); box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);">
      <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 6px;">${escapeHtml(label)}</div>
      <div style="font-size: 16px; font-weight: 700; line-height: 1.5;">${escapeHtml(value)}</div>
    </div>
  `;
}

function tagBlock(title, items, background, color, fullWidth) {
  const tags = items.length
    ? items.map((item) => `<span style="display: inline-flex; align-items: center; padding: 6px 10px; border-radius: 999px; background: rgba(255,255,255,0.8); margin: 0 8px 8px 0;">${escapeHtml(item)}</span>`).join("")
    : `<span style="color: var(--text-muted);">待补充</span>`;
  const width = fullWidth ? "grid-column: 1 / -1;" : "";

  return `
    <div style="border-radius: 14px; padding: 14px; background: ${background}; color: ${color}; ${width}">
      <div style="font-size: 12px; font-weight: 700; margin-bottom: 10px;">${escapeHtml(title)}</div>
      <div style="line-height: 1.8;">${tags}</div>
    </div>
  `;
}

function detailBlock(title, value, hint) {
  return `
    <div style="border-radius: 14px; padding: 14px; background: #ffffff; border: 1px solid rgba(15, 23, 42, 0.08);">
      <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 8px;">${escapeHtml(title)}</div>
      <div style="font-size: 14px; font-weight: 600; line-height: 1.7;">${escapeHtml(value)}</div>
      <div style="font-size: 12px; color: var(--text-muted); margin-top: 8px; line-height: 1.6;">${escapeHtml(hint)}</div>
    </div>
  `;
}

function pill(value, color, background) {
  return `<span style="display: inline-flex; align-items: center; padding: 6px 10px; border-radius: 999px; color: ${color}; background: ${background}; font-size: 12px; font-weight: 700;">${escapeHtml(value)}</span>`;
}

function splitItems(value) {
  return String(value || "")
    .split(/[\n,，；;、]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function formatSalary(currency, min, max) {
  if (!min && !max) {
    return "待补充";
  }
  const parts = [currency || "", min || "--", max ? `- ${max}` : ""].filter(Boolean);
  return parts.join(" ").trim();
}

function priorityLabel(value) {
  const labels = {
    Critical: "关键补位",
    High: "优先推进",
    Normal: "常规推进",
  };
  return labels[value] || value || "优先级待确认";
}

function workModeLabel(value) {
  const labels = {
    Onsite: "现场办公",
    Hybrid: "混合办公",
    Remote: "远程办公",
  };
  return labels[value] || value || "模式待确认";
}

function renderRequisitionEmpty(message) {
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
