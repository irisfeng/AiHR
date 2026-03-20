frappe.ui.form.on("Job Opening", {
  refresh(frm) {
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
        frappe.show_alert({ message: "岗位发布包已同步", indicator: "green" });
      });
    }

    frm.add_custom_button("批量 AI 初筛", async () => {
      const response = await frappe.call({
        method: "aihr.api.recruitment.screen_job_opening_applicants",
        args: { job_opening: frm.doc.name, save: 1 },
        freeze: true,
        freeze_message: "正在批量生成候选人摘要卡...",
      });
      const result = response.message || {};
      frappe.msgprint(`已完成 ${result.screened_count || 0} 位候选人的 AI 初筛。`);
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
