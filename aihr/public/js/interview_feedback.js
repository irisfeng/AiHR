frappe.ui.form.on("Interview Feedback", {
  async refresh(frm) {
    await renderFeedbackSnapshot(frm);

    if (frm.is_new()) {
      return;
    }

    if (frm.doc.interview && frm.doc.docstatus === 0) {
      frm.add_custom_button("加载评分项", async () => {
        await loadFeedbackBlueprint(frm, true);
      });

      frm.add_custom_button("应用面试结论", async () => {
        if (frm.doc.docstatus === 0) {
          await frm.save();
        }
        await frappe.call({
          method: "aihr.api.recruitment.apply_interview_feedback",
          args: { interview_feedback: frm.doc.name, save: 1 },
          freeze: true,
          freeze_message: "正在同步面试结论...",
        });
        await frm.reload_doc();
        await renderFeedbackSnapshot(frm);
        frappe.show_alert({ message: "面试结论已同步到主流程", indicator: "green" });
      });
    }

    if (frm.doc.interview) {
      frm.add_custom_button("查看面试协同", () => {
        frappe.set_route("Form", "Interview", frm.doc.interview);
      });
    }
  },

  async interview(frm) {
    if (!frm.doc.interview) {
      return;
    }
    await loadFeedbackBlueprint(frm, false);
  },
});

async function loadFeedbackBlueprint(frm, showAlert) {
  if (!frm.doc.interview) {
    frappe.msgprint("请先选择面试记录。");
    return;
  }

  const response = await frappe.call({
    method: "aihr.api.recruitment.get_interview_feedback_blueprint",
    args: { interview: frm.doc.interview },
  });
  const blueprint = response.message || {};
  const existingSkills = new Set((frm.doc.skill_assessment || []).map((row) => row.skill));

  if (!frm.doc.interviewer && blueprint.interviewer) {
    frm.set_value("interviewer", blueprint.interviewer);
  }
  if (!frm.doc.aihr_next_step_suggestion && blueprint.next_step_suggestion) {
    frm.set_value("aihr_next_step_suggestion", blueprint.next_step_suggestion);
  }
  if (!frm.doc.aihr_hiring_recommendation && blueprint.hiring_recommendation) {
    frm.set_value("aihr_hiring_recommendation", blueprint.hiring_recommendation);
  }

  (blueprint.skill_assessment || []).forEach((row) => {
    if (existingSkills.has(row.skill)) {
      return;
    }
    frm.add_child("skill_assessment", row);
  });

  frm.refresh_field("skill_assessment");
  if (showAlert) {
    frappe.show_alert({ message: "评分项已加载", indicator: "green" });
  }
}

async function renderFeedbackSnapshot(frm) {
  const field = frm.get_field("aihr_feedback_snapshot_html");
  if (!field) {
    return;
  }

  if (frm.is_new()) {
    field.$wrapper.html(renderEmpty("先保存反馈单，再生成 AIHR 反馈概览。"));
    return;
  }

  const response = await frappe.call({
    method: "aihr.api.recruitment.get_interview_feedback_snapshot",
    args: { interview_feedback: frm.doc.name },
  });
  const data = response.message || {};
  const feedback = data.interview_feedback || {};
  const interview = data.interview || {};
  const applicant = data.job_applicant || {};
  const opening = data.job_opening || {};
  const screening = data.screening || null;
  const actions = data.actions || {};

  field.$wrapper.html(`
    <div style="border-radius: 18px; padding: 20px; background: linear-gradient(135deg, #fff7ed, #ffffff 45%, #f8fafc); border: 1px solid rgba(245, 158, 11, 0.18);">
      <div style="display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; margin-bottom: 18px; flex-wrap: wrap;">
        <div style="max-width: 58%;">
          <div style="font-size: 12px; letter-spacing: 0.08em; text-transform: uppercase; color: #c2410c; font-weight: 700;">AIHR 反馈概览</div>
          <div style="font-size: 28px; font-weight: 700; margin-top: 6px; color: #0f172a;">${escapeHtml(applicant.applicant_name || "面试反馈")}</div>
          <div style="margin-top: 8px; color: var(--text-muted); line-height: 1.7;">
            ${escapeHtml(opening.job_title || "未关联岗位")} · ${escapeHtml(interview.interview_round || "轮次待补充")}
          </div>
        </div>
        <div style="min-width: 280px; border-radius: 16px; padding: 16px; background: #0f172a; color: #fff;">
          <div style="font-size: 12px; color: rgba(255,255,255,0.72);">下一步建议</div>
          <div style="margin-top: 10px; font-size: 15px; font-weight: 700; line-height: 1.7;">${escapeHtml(feedback.next_step_suggestion || actions.next_action || "先补反馈，再同步结论")}</div>
        </div>
      </div>

      <div style="display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-bottom: 18px;">
        ${metricCard("面试结论", statusLabel(feedback.result))}
        ${metricCard("平均评分", formatRating(feedback.average_rating))}
        ${metricCard("面试官", feedback.interviewer || "待分配")}
        ${metricCard("建议", feedback.hiring_recommendation || "待判断")}
      </div>

      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
        <div style="display: grid; gap: 14px;">
          <div style="border-radius: 16px; padding: 16px; background: #ffffff; border: 1px solid rgba(15, 23, 42, 0.08);">
            <div style="font-size: 13px; color: var(--text-muted); margin-bottom: 10px;">反馈摘要</div>
            <div style="font-size: 13px; line-height: 1.8; white-space: pre-wrap;">${escapeHtml(actions.summary || "待补充反馈摘要。")}</div>
          </div>
          <div style="border-radius: 16px; padding: 16px; background: #ffffff; border: 1px solid rgba(15, 23, 42, 0.08);">
            <div style="font-size: 13px; color: var(--text-muted); margin-bottom: 10px;">面试官原始反馈</div>
            <div style="font-size: 14px; line-height: 1.8;">${escapeHtml(feedback.feedback || "待补充。")}</div>
          </div>
        </div>
        <div style="display: grid; gap: 14px;">
          <div style="border-radius: 16px; padding: 16px; background: #ffffff; border: 1px solid rgba(15, 23, 42, 0.08);">
            <div style="font-size: 13px; color: var(--text-muted); margin-bottom: 10px;">候选人 AI 摘要</div>
            <div style="font-size: 14px; line-height: 1.8;">${escapeHtml((screening && screening.ai_summary) || "暂无 AI 摘要。")}</div>
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
    <div style="border-radius: 14px; padding: 14px; background: #ffffff; border: 1px solid rgba(15,23,42,0.08);">
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
    <div style="border-radius: 14px; padding: 14px; background: #ffffff; border: 1px solid rgba(15,23,42,0.08);">
      <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 8px;">${escapeHtml(title)}</div>
      <ul style="padding-left: 18px; margin: 0; line-height: 1.7;">${listItems}</ul>
    </div>
  `;
}

function statusLabel(value) {
  const labels = {
    Cleared: "建议通过",
    Rejected: "建议淘汰",
  };

  return labels[value] || value || "待确认";
}

function formatRating(value) {
  if (!value) {
    return "待补充";
  }
  return `${Number(value).toFixed(1)} / 5`;
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
