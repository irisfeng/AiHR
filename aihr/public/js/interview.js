frappe.ui.form.on("Interview", {
  async refresh(frm) {
    await renderInterviewSnapshot(frm);

    if (frm.is_new()) {
      return;
    }

    frm.add_custom_button("生成面试官资料包", async () => {
      await frappe.call({
        method: "aihr.api.recruitment.prepare_interviewer_pack",
        args: { interview: frm.doc.name, save: 1 },
        freeze: true,
        freeze_message: "正在生成面试官资料包...",
      });
      await frm.reload_doc();
      await renderInterviewSnapshot(frm);
      frappe.show_alert({ message: "面试官资料包已更新", indicator: "green" });
    });

    frm.add_custom_button("同步跟进动作", async () => {
      await frappe.call({
        method: "aihr.api.recruitment.sync_interview_follow_up",
        args: { interview: frm.doc.name, save: 1 },
        freeze: true,
        freeze_message: "正在同步面试跟进动作...",
      });
      await frm.reload_doc();
      await renderInterviewSnapshot(frm);
      frappe.show_alert({ message: "面试跟进动作已同步", indicator: "green" });
    });

    if (frm.doc.job_applicant) {
      frm.add_custom_button("查看候选人摘要", () => {
        frappe.set_route("Form", "Job Applicant", frm.doc.job_applicant);
      });
    }

    if (frm.doc.job_applicant && frm.doc.status === "Cleared") {
      frm.add_custom_button("发起 Offer", async () => {
        const defaults = {
          job_applicant: frm.doc.job_applicant,
          offer_date: frappe.datetime.get_today(),
        };
        if (frm.doc.job_opening) {
          const response = await frappe.db.get_value("Job Opening", frm.doc.job_opening, ["company", "designation"]);
          const opening = response.message || {};
          defaults.company = opening.company;
          defaults.designation = opening.designation;
        }
        frappe.new_doc("Job Offer", defaults);
      });
    }
  },
});

async function renderInterviewSnapshot(frm) {
  const field = frm.get_field("aihr_interview_snapshot_html");
  if (!field) {
    return;
  }

  if (frm.is_new()) {
    field.$wrapper.html(renderInterviewEmpty("先保存面试安排，再生成 AIHR 面试协同面板。"));
    return;
  }

  const response = await frappe.call({
    method: "aihr.api.recruitment.get_interview_snapshot",
    args: { interview: frm.doc.name },
  });

  const data = response.message || {};
  const interview = data.interview || {};
  const applicant = data.job_applicant || {};
  const opening = data.job_opening || {};
  const screening = data.screening || null;
  const actions = data.actions || {};
  const interviewerPack = interview.interviewer_pack || "";

  field.$wrapper.html(`
    <div style="border-radius: 18px; padding: 20px; background: linear-gradient(135deg, #172554, #1e3a5f 52%, #23435c 100%); color: #fff; border: 1px solid rgba(15, 23, 42, 0.12); overflow: hidden;">
      <div style="display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; margin-bottom: 18px; flex-wrap: wrap;">
        <div style="max-width: 58%;">
          <div style="font-size: 12px; letter-spacing: 0.08em; text-transform: uppercase; color: rgba(255,255,255,0.72); font-weight: 700;">AIHR Interview Control Room</div>
          <div style="font-size: 28px; font-weight: 700; margin-top: 6px;">${escapeHtml(applicant.applicant_name || frm.doc.job_applicant || "候选人面试")}</div>
          <div style="margin-top: 8px; color: rgba(255,255,255,0.8); line-height: 1.7;">
            ${escapeHtml(opening.job_title || "未关联岗位")} · ${escapeHtml(interview.interview_round || "轮次待补充")}
          </div>
        </div>
        <div style="min-width: 280px; border-radius: 16px; padding: 16px; background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.08); backdrop-filter: blur(6px);">
          <div style="font-size: 12px; color: rgba(255,255,255,0.72);">当前跟进建议</div>
          <div style="margin-top: 10px; font-size: 15px; font-weight: 700; line-height: 1.7;">${escapeHtml(actions.next_action || "确认面试安排与反馈节奏")}</div>
          <div style="margin-top: 10px; font-size: 12px; color: rgba(255,255,255,0.72);">让 HR 和面试官在一屏里看到候选人摘要、风险点和反馈截止时间。</div>
        </div>
      </div>

      <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 18px;">
        ${chip(statusLabel(interview.status), "rgba(255,255,255,0.14)")}
        ${chip(interview.interview_mode || "形式待确认", "rgba(245,158,11,0.22)")}
        ${chip(interview.schedule_label || "时间待安排", "rgba(14,165,233,0.18)")}
        ${chip(interview.follow_up_owner || "待分配跟进人", "rgba(16,185,129,0.18)")}
      </div>

      <div style="display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-bottom: 18px;">
        ${metricCard("匹配分", formatScore(applicant.aihr_match_score))}
        ${metricCard("安排时间", interview.schedule_label || "待安排")}
        ${metricCard("反馈截止", interview.feedback_due_label || "待同步")}
        ${metricCard("面试官", formatPeople(interview.interviewers))}
      </div>

      <div style="display: grid; grid-template-columns: 1.1fr 0.9fr; gap: 14px;">
        <div style="border-radius: 16px; padding: 16px; background: #ffffff; color: #0f172a;">
          <div style="font-size: 13px; color: var(--text-muted); margin-bottom: 10px;">候选人面试要点</div>
          ${screening ? renderInsightBlock(screening, applicant) : renderNoScreening()}
        </div>
        <div style="display: grid; gap: 14px;">
          <div style="border-radius: 16px; padding: 16px; background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.08);">
            <div style="font-size: 13px; color: rgba(255,255,255,0.72); margin-bottom: 10px;">建议追问问题</div>
            ${questionList(screening ? screening.suggested_questions : [])}
          </div>
          <div style="border-radius: 16px; padding: 16px; background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.08);">
            <div style="font-size: 13px; color: rgba(255,255,255,0.72); margin-bottom: 10px;">面试官资料包</div>
            <div style="font-size: 13px; line-height: 1.75; white-space: pre-wrap; color: rgba(255,255,255,0.9); max-height: 280px; overflow: auto;">${escapeHtml(interviewerPack || "点击“生成面试官资料包”后，这里会自动整合候选人摘要、面试重点和建议追问。")}</div>
          </div>
        </div>
      </div>
    </div>
  `);
}

function renderInsightBlock(screening, applicant) {
  return `
    <div style="display: grid; gap: 14px;">
      <div>
        <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 6px;">AI 候选人摘要</div>
        <div style="line-height: 1.7;">${escapeHtml(screening.ai_summary || "暂无摘要")}</div>
      </div>
      <div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px;">
        ${listBlock("优势", screening.strengths)}
        ${listBlock("风险点", screening.risks)}
      </div>
      <div style="border-radius: 14px; padding: 14px; background: #f8fafc; border: 1px solid rgba(15, 23, 42, 0.08);">
        <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 6px;">候选人当前动作</div>
        <div style="font-size: 14px; font-weight: 600;">${escapeHtml(applicant.aihr_next_action || "待确认")}</div>
      </div>
    </div>
  `;
}

function renderNoScreening() {
  return `
    <div style="border: 1px dashed rgba(15,23,42,0.12); border-radius: 14px; padding: 16px; color: var(--text-muted); line-height: 1.7;">
      当前还没有 AI 摘要卡。建议先回到候选人页运行 AI 初筛，再安排面试官查看资料包。
    </div>
  `;
}

function listBlock(title, items) {
  const listItems = (items || []).length
    ? (items || []).map((item) => `<li style="margin-bottom: 4px;">${escapeHtml(item)}</li>`).join("")
    : "<li style=\"margin-bottom: 4px;\">暂无</li>";

  return `
    <div style="border-radius: 14px; padding: 14px; background: #f8fafc;">
      <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 8px;">${escapeHtml(title)}</div>
      <ul style="padding-left: 18px; margin: 0;">${listItems}</ul>
    </div>
  `;
}

function questionList(items) {
  if (!(items || []).length) {
    return `<div style="color: rgba(255,255,255,0.72); line-height: 1.7;">暂无建议追问问题。</div>`;
  }

  return `
    <ol style="padding-left: 18px; margin: 0; color: rgba(255,255,255,0.92); line-height: 1.8;">
      ${(items || []).map((item) => `<li style="margin-bottom: 6px;">${escapeHtml(item)}</li>`).join("")}
    </ol>
  `;
}

function metricCard(label, value) {
  return `
    <div style="border-radius: 14px; padding: 14px; background: rgba(255,255,255,0.1); backdrop-filter: blur(4px);">
      <div style="font-size: 12px; color: rgba(255,255,255,0.72); margin-bottom: 6px;">${escapeHtml(label)}</div>
      <div style="font-size: 16px; font-weight: 700; line-height: 1.6;">${escapeHtml(value)}</div>
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

function formatScore(value) {
  if (value === null || value === undefined || value === "" || Number.isNaN(Number(value))) {
    return "--";
  }
  return `${Number(value).toFixed(0)} 分`;
}

function formatPeople(values) {
  if (!(values || []).length) {
    return "待补充";
  }
  return values.join(" / ");
}

function statusLabel(value) {
  const labels = {
    Pending: "待进行",
    "Under Review": "待反馈汇总",
    Cleared: "建议通过",
    Rejected: "已淘汰",
  };

  return labels[value] || value || "待确认";
}

function renderInterviewEmpty(message) {
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
