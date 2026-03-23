const AI_SCREENING_DETAIL_FIELDS = [
  "job_applicant",
  "job_opening",
  "status",
  "overall_score",
  "matched_skills",
  "missing_skills",
  "ai_summary",
  "strengths",
  "risks",
  "suggested_questions",
];

const AI_SCREENING_DEBUG_FIELDS = [
  "payload_section",
  "parsed_resume_json",
  "screening_payload_json",
];

const AI_SCREENING_FOCUS_CLASS = "aihr-ai-screening-focus";

frappe.ui.form.on("AI Screening", {
  onload_post_render(frm) {
    applyAIScreeningFocusMode(frm);
  },

  async refresh(frm) {
    applyAIScreeningFocusMode(frm);
    syncScreeningFieldVisibility(frm);
    await renderAIScreeningReview(frm);
    refreshAIScreeningButtons(frm);
    frappe.utils.defer(() => applyAIScreeningFocusMode(frm));
  },
});

function syncScreeningFieldVisibility(frm) {
  AI_SCREENING_DETAIL_FIELDS.forEach((fieldname) => frm.toggle_display(fieldname, false));
  AI_SCREENING_DEBUG_FIELDS.forEach((fieldname) => frm.toggle_display(fieldname, Boolean(frm._aihr_show_debug)));
}

async function renderAIScreeningReview(frm) {
  const field = frm.get_field("aihr_review_snapshot_html");
  if (!field) {
    return;
  }

  if (frm.is_new()) {
    field.$wrapper.html(renderReviewEmpty("保存 AI 初筛结果后，这里会显示简历预览和 AI 摘要。"));
    return;
  }

  field.$wrapper.html(renderReviewLoading());

  try {
    const response = await frappe.call({
      method: "aihr.api.recruitment.get_ai_screening_snapshot",
      args: { ai_screening: frm.doc.name },
    });
    frm._aihr_screening_snapshot = response.message || {};
    field.$wrapper.html(renderReviewLayout(frm._aihr_screening_snapshot));
  } catch (error) {
    console.error(error);
    field.$wrapper.html(renderReviewEmpty("AI 初筛决策页加载失败，请刷新页面后重试。"));
  }
}

function refreshAIScreeningButtons(frm) {
  if (frm.is_new()) {
    return;
  }

  removeInnerButton(frm, "查看候选人档案");
  removeInnerButton(frm, "打开原始简历");
  removeInnerButton(frm, "查看解析调试");
  removeInnerButton(frm, "隐藏解析调试");

  const snapshot = frm._aihr_screening_snapshot || {};
  const applicant = snapshot.job_applicant || {};
  const resumePreview = snapshot.resume_preview || {};

  if (applicant.name) {
    frm.add_custom_button("查看候选人档案", () => {
      frappe.set_route("Form", "Job Applicant", applicant.name);
    });
  }

  if (resumePreview.file_url) {
    frm.add_custom_button("打开原始简历", () => {
      window.open(resumePreview.preview_url || resumePreview.file_url, "_blank", "noopener,noreferrer");
    });
  }

  frm.add_custom_button(frm._aihr_show_debug ? "隐藏解析调试" : "查看解析调试", () => {
    frm._aihr_show_debug = !frm._aihr_show_debug;
    syncScreeningFieldVisibility(frm);
    refreshAIScreeningButtons(frm);
  });
}

function renderReviewLayout(data) {
  const screening = data.screening || {};
  const applicant = data.job_applicant || {};
  const opening = data.job_opening || {};
  const requisition = data.job_requisition || {};
  const preview = data.resume_preview || {};

  const supplierText = [applicant.resume_supplier, applicant.resume_source_channel].filter(Boolean).join(" / ") || "未填写";
  const targetCity = requisition.work_city || "未设置";

  return `
    <div style="display: grid; grid-template-columns: minmax(0, 1.02fr) minmax(360px, 0.98fr); gap: 16px; align-items: stretch;">
      <section style="border: 1px solid rgba(15, 23, 42, 0.08); border-radius: 18px; background: #fff; padding: 18px; box-shadow: 0 18px 36px rgba(15, 23, 42, 0.04);">
        <div style="display:flex; justify-content:space-between; gap:16px; align-items:flex-start; margin-bottom:16px;">
          <div>
            <div style="font-size:12px; color:#64748b; margin-bottom:6px;">候选人 AI 决策卡</div>
            <div style="font-size:28px; line-height:1.15; font-weight:700; color:#0f172a;">${escapeHtml(applicant.applicant_name || applicant.name || "候选人")}</div>
            <div style="font-size:14px; color:#526173; margin-top:8px;">${escapeHtml(opening.job_title || "未关联岗位")} · ${escapeHtml(applicant.candidate_city || "城市待补充")}</div>
          </div>
          <div style="text-align:right;">
            <div style="display:inline-flex; padding:6px 12px; border-radius:999px; background:${statusTone(screening.status).background}; color:${statusTone(screening.status).text}; font-size:12px; font-weight:700;">${escapeHtml(screening.status_label || screening.status || "待确认")}</div>
            <div style="font-size:32px; font-weight:800; color:#0f172a; margin-top:10px;">${formatScore(screening.overall_score)}</div>
            <div style="font-size:12px; color:#64748b;">AI 初筛匹配分</div>
          </div>
        </div>

        <div style="display:grid; grid-template-columns:repeat(4, minmax(0, 1fr)); gap:10px; margin-bottom:16px;">
          ${metricCard("岗位名称", opening.job_title || "未关联")}
          ${metricCard("工作年限", formatYears(applicant.years_of_experience))}
          ${metricCard("目标城市", targetCity)}
          ${metricCard("来源", supplierText)}
        </div>

        <div style="border-radius:14px; background:#f8fafc; padding:14px; margin-bottom:14px;">
          <div style="font-size:12px; color:#64748b; margin-bottom:6px;">AI 摘要</div>
          <div style="font-size:14px; line-height:1.75; color:#0f172a;">${escapeHtml(screening.ai_summary || "暂无摘要")}</div>
        </div>

        <div style="display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); gap:12px; margin-bottom:14px;">
          ${chipBlock("匹配技能", screening.matched_skills, "#ecfdf5", "#0f766e")}
          ${chipBlock("缺失技能", screening.missing_skills, "#fff7ed", "#c2410c")}
        </div>

        <div style="display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); gap:12px; margin-bottom:14px;">
          ${listBlock("推荐理由", screening.strengths, "当前候选人最值得推进的点。")}
          ${listBlock("风险点", screening.risks, "需要经理或 HR 特别确认的点。")}
        </div>

        ${listBlock("建议追问问题", screening.suggested_questions, "建议在电话初筛或面试时重点核实。")}

        <div style="margin-top:14px; display:flex; gap:10px; flex-wrap:wrap;">
          ${routeLink(applicant.route, "进入候选人档案")}
          ${routeLink(opening.route, "返回招聘中岗位")}
          ${routeLink(requisition.route, "查看岗位需求")}
        </div>
      </section>

      <section style="border: 1px solid rgba(15, 23, 42, 0.08); border-radius: 18px; background: #fff; padding: 18px; box-shadow: 0 18px 36px rgba(15, 23, 42, 0.04); display:flex; flex-direction:column;">
        <div style="display:flex; justify-content:space-between; gap:12px; align-items:flex-start; margin-bottom:12px;">
          <div>
            <div style="font-size:12px; color:#64748b; margin-bottom:6px;">原始简历</div>
            <div style="font-size:18px; font-weight:700; color:#0f172a;">${escapeHtml(preview.file_name || "未找到原始附件")}</div>
          </div>
          ${preview.preview_url ? `<a href="${escapeHtml(preview.preview_url)}" target="_blank" rel="noreferrer" style="font-size:12px; font-weight:700; color:#0f766e; text-decoration:none;">打开原件</a>` : ""}
        </div>

        <div style="font-size:12px; color:#64748b; margin-bottom:12px;">
          解析状态：${escapeHtml(applicant.resume_parse_status || "待确认")} · 供应商：${escapeHtml(supplierText)}
        </div>

        ${renderPreviewPanel(preview)}
      </section>
    </div>
  `;
}

function renderPreviewPanel(preview) {
  if (preview.can_embed && preview.preview_url) {
    return `
      <div style="border-radius:16px; overflow:hidden; border:1px solid rgba(15, 23, 42, 0.08); min-height:920px; background:#f8fafc;">
        <iframe src="${escapeHtml(preview.preview_url)}#toolbar=0&navpanes=0&scrollbar=1" style="width:100%; min-height:920px; border:0; background:#fff;" title="简历预览"></iframe>
      </div>
    `;
  }

  if (preview.preview_url || preview.file_url) {
    return `
      <div style="border-radius:16px; border:1px dashed rgba(15, 23, 42, 0.16); background:#f8fafc; padding:18px; color:#526173; line-height:1.8;">
        当前附件格式暂不支持站内嵌入预览，请点击右上角“打开原件”查看电子版简历。
      </div>
      ${preview.text_excerpt ? renderTextExcerpt(preview.text_excerpt) : ""}
    `;
  }

  if (preview.text_excerpt) {
    return renderTextExcerpt(preview.text_excerpt);
  }

  return `
    <div style="border-radius:16px; border:1px dashed rgba(15, 23, 42, 0.16); background:#f8fafc; padding:18px; color:#526173; line-height:1.8;">
      当前没有可预览的简历附件。建议优先通过 ZIP 简历包导入候选人，并保留原始 PDF 以便经理复核。
    </div>
  `;
}

function renderTextExcerpt(text) {
  return `
    <div style="border-radius:16px; border:1px solid rgba(15, 23, 42, 0.08); background:#f8fafc; padding:16px; min-height:320px; overflow:auto; white-space:pre-wrap; line-height:1.8; color:#334155;">
      ${escapeHtml(text)}
    </div>
  `;
}

function chipBlock(title, items, background, color) {
  const content = (items || []).length
    ? items.map((item) => `<span style="display:inline-flex; align-items:center; padding:6px 10px; border-radius:999px; background:${background}; color:${color}; font-size:12px; font-weight:700;">${escapeHtml(item)}</span>`).join("")
    : `<span style="font-size:13px; color:#64748b;">暂无</span>`;

  return `
    <div style="border-radius:14px; background:#f8fafc; padding:14px;">
      <div style="font-size:12px; color:#64748b; margin-bottom:8px;">${escapeHtml(title)}</div>
      <div style="display:flex; flex-wrap:wrap; gap:8px;">${content}</div>
    </div>
  `;
}

function listBlock(title, items, hint) {
  const listItems = (items || []).length
    ? items.map((item) => `<li style="margin-bottom:6px;">${escapeHtml(item)}</li>`).join("")
    : `<li style="margin-bottom:6px;">暂无</li>`;

  return `
    <div style="border-radius:14px; background:#f8fafc; padding:14px;">
      <div style="font-size:12px; color:#64748b; margin-bottom:6px;">${escapeHtml(title)}</div>
      <div style="font-size:12px; color:#94a3b8; margin-bottom:8px;">${escapeHtml(hint || "")}</div>
      <ul style="padding-left:18px; margin:0; line-height:1.7; color:#0f172a;">${listItems}</ul>
    </div>
  `;
}

function metricCard(label, value) {
  return `
    <div style="border-radius:12px; padding:12px; background:#f8fafc;">
      <div style="font-size:12px; color:#64748b; margin-bottom:4px;">${escapeHtml(label)}</div>
      <div style="font-size:14px; font-weight:700; color:#0f172a;">${escapeHtml(value || "未填写")}</div>
    </div>
  `;
}

function routeLink(url, label) {
  if (!url) {
    return "";
  }
  return `<a href="${escapeHtml(url)}" style="display:inline-flex; align-items:center; padding:8px 12px; border-radius:999px; background:#eef6ff; color:#1658b7; font-size:12px; font-weight:700; text-decoration:none;">${escapeHtml(label)}</a>`;
}

function renderReviewLoading() {
  return `
    <div style="border:1px dashed rgba(15, 23, 42, 0.14); border-radius:18px; padding:18px; background:#fff; color:#64748b;">
      正在整理 AI 初筛决策页...
    </div>
  `;
}

function renderReviewEmpty(message) {
  return `
    <div style="border:1px dashed rgba(15, 23, 42, 0.14); border-radius:18px; padding:18px; background:#fff; color:#64748b;">
      ${escapeHtml(message)}
    </div>
  `;
}

function statusTone(status) {
  const tones = {
    Advance: { background: "#ecfdf5", text: "#0f766e" },
    "Ready for Review": { background: "#eff6ff", text: "#1658b7" },
    Hold: { background: "#fff7ed", text: "#c2410c" },
    Reject: { background: "#fef2f2", text: "#b91c1c" },
  };
  return tones[status] || { background: "#f1f5f9", text: "#334155" };
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

function removeInnerButton(frm, label) {
  if (frm.page && frm.page.remove_inner_button) {
    frm.page.remove_inner_button(label);
  }
}

function applyAIScreeningFocusMode(frm) {
  ensureAIScreeningFocusStyles();

  const $wrapper = $(frm.wrapper);
  const $page = $(frm.page && frm.page.wrapper);
  const $mainSection = $wrapper.closest(".layout-main-section");
  const $layoutParent = $mainSection.parent();
  const $pageContent = $page.closest(".page-content");

  $wrapper.addClass(AI_SCREENING_FOCUS_CLASS);
  $page.addClass(AI_SCREENING_FOCUS_CLASS);
  $mainSection.addClass(AI_SCREENING_FOCUS_CLASS);
  $layoutParent.addClass(AI_SCREENING_FOCUS_CLASS);
  $pageContent.addClass(AI_SCREENING_FOCUS_CLASS);

  $pageContent.find(".layout-side-section, .form-sidebar, .form-footer").hide();
  $pageContent.find(".layout-side-section, .form-sidebar, .form-footer").css("display", "none");
  $pageContent.find(".layout-main-section-wrapper").css({ width: "100%", "max-width": "none", flex: "1 1 100%" });
  $wrapper.find(".form-dashboard-section, .form-links, .comment-box, .timeline, .timeline-items, .timeline-actions, .timeline-label").hide();
  $wrapper.find(".form-section:has(.comment-box), .form-section:has(.timeline-items), .form-section:has(.timeline)").hide();
}

function ensureAIScreeningFocusStyles() {
  if (document.getElementById("aihr-ai-screening-focus-style")) {
    return;
  }

  const style = document.createElement("style");
  style.id = "aihr-ai-screening-focus-style";
  style.textContent = `
    .${AI_SCREENING_FOCUS_CLASS}.layout-main-section,
    .${AI_SCREENING_FOCUS_CLASS} .layout-main-section {
      max-width: none !important;
      width: 100% !important;
    }

    .${AI_SCREENING_FOCUS_CLASS} .layout-main-section-wrapper {
      width: 100% !important;
      max-width: none !important;
    }

    .${AI_SCREENING_FOCUS_CLASS} .form-layout {
      gap: 0 !important;
    }

    .${AI_SCREENING_FOCUS_CLASS} .layout-side-section,
    .${AI_SCREENING_FOCUS_CLASS} .form-sidebar,
    .${AI_SCREENING_FOCUS_CLASS} .form-dashboard-section,
    .${AI_SCREENING_FOCUS_CLASS} .comment-box,
    .${AI_SCREENING_FOCUS_CLASS} .timeline,
    .${AI_SCREENING_FOCUS_CLASS} .timeline-items,
    .${AI_SCREENING_FOCUS_CLASS} .timeline-actions,
    .${AI_SCREENING_FOCUS_CLASS} .timeline-label,
    .${AI_SCREENING_FOCUS_CLASS} .form-footer {
      display: none !important;
    }

    .${AI_SCREENING_FOCUS_CLASS} .form-column.col-sm-8,
    .${AI_SCREENING_FOCUS_CLASS} .form-column.col-sm-12,
    .${AI_SCREENING_FOCUS_CLASS} .form-page {
      width: 100% !important;
      max-width: none !important;
    }

    .${AI_SCREENING_FOCUS_CLASS} .form-section:last-child {
      margin-bottom: 0 !important;
    }
  `;
  document.head.appendChild(style);
}

function escapeHtml(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
