frappe.ui.form.on("Job Requisition", {
  async refresh(frm) {
    frm.set_df_property("status", "read_only", 1);
    frm.set_df_property("designation", "hidden", 1);
    frm.set_df_property("requested_by_designation", "hidden", 1);
    syncRequisitionTitleFields(frm, { syncFromDesignation: true });
    await applyRequisitionDefaults(frm);
    configureRequisitionEntryForm(frm);
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

    if (frm.doc.status === "Open & Approved" && canCreateJobOpening()) {
      const jobTitle = getRequisitionJobTitle(frm.doc);
      frm.add_custom_button("新建招聘中岗位", () => {
        frappe.new_doc("Job Opening", {
          job_requisition: frm.doc.name,
          job_title: jobTitle,
          designation: jobTitle,
          department: frm.doc.department,
        });
      });
    }
  },

  aihr_job_title(frm) {
    syncRequisitionTitleFields(frm);
    renderRequisitionSnapshot(frm);
  },

  aihr_role_description_input(frm) {
    syncRequisitionDescriptionFields(frm);
  },

  designation(frm) {
    syncRequisitionTitleFields(frm, { syncFromDesignation: true });
    renderRequisitionSnapshot(frm);
  },

  description(frm) {
    syncRequisitionDescriptionFields(frm, { syncFromDescription: true });
  },

  validate(frm) {
    syncRequisitionTitleFields(frm);
    syncRequisitionDescriptionFields(frm);
    ensureRequesterDefaults(frm);

    if (isHiringManagerOnly() && !(frm.doc.aihr_role_description_input || "").trim()) {
      focusManagerDescription(frm);
      frappe.msgprint("请先填写岗位职责与要求，再保存岗位需求单。");
      frappe.validated = false;
      return false;
    }

    if (!(frm.doc.requested_by || "").trim()) {
      frappe.msgprint("需求提出人会自动带入当前登录经理，请刷新页面后重试。");
      frappe.validated = false;
      return false;
    }
  },
});

function renderRequisitionSnapshot(frm) {
  const field = frm.get_field("aihr_role_snapshot_html");
  if (!field) {
    return;
  }

  if (frm.is_new()) {
    field.$wrapper.html(renderRequisitionEmpty("先保存岗位需求，再生成 AIHR 岗位概览卡。"));
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
          <div style="font-size: 12px; letter-spacing: 0.08em; text-transform: uppercase; color: #0f766e; font-weight: 700;">AIHR 岗位概览</div>
          <div style="font-size: 26px; font-weight: 700; margin-top: 6px;">${escapeHtml(getRequisitionJobTitle(frm.doc) || "待命名岗位")}</div>
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

function canCreateJobOpening() {
  const roles = Array.isArray(frappe.user_roles) ? frappe.user_roles : [];
  return roles.includes("HR Manager") || roles.includes("System Manager");
}

function isHiringManagerOnly() {
  const roles = Array.isArray(frappe.user_roles) ? frappe.user_roles : [];
  return roles.includes("AIHR Hiring Manager") && !roles.includes("HR Manager") && !roles.includes("System Manager");
}

async function applyRequisitionDefaults(frm) {
  if (!frm.is_new() || frm.__aihr_defaults_loaded) {
    return;
  }

  try {
    frm.__aihr_defaults_loaded = true;
    const response = await frappe.call({
      method: "aihr.api.recruitment.get_job_requisition_defaults",
    });
    const defaults = response.message || {};
    frm.__aihr_requisition_defaults = defaults;

    await populateRequesterDefaults(frm, defaults);
  } catch (error) {
    frm.__aihr_defaults_loaded = false;
    console.warn("AIHR requisition defaults unavailable", error);
  }
}

async function populateRequesterDefaults(frm, defaults) {
  if (!defaults) {
    return;
  }

  if (!frm.doc.requested_by && defaults.requested_by) {
    await frm.set_value("requested_by", defaults.requested_by);
  }
  if (!frm.doc.requested_by_name && defaults.requested_by_name) {
    await frm.set_value("requested_by_name", defaults.requested_by_name);
  }
  if (!frm.doc.aihr_requested_by_title && defaults.requester_title) {
    await frm.set_value("aihr_requested_by_title", defaults.requester_title);
  }
  if (!frm.doc.requested_by_dept && defaults.department) {
    await frm.set_value("requested_by_dept", defaults.department);
  }
  if (!frm.doc.department && defaults.department) {
    await frm.set_value("department", defaults.department);
  }
}

function ensureRequesterDefaults(frm) {
  const defaults = frm.__aihr_requisition_defaults || {};
  if (!defaults) {
    return;
  }

  if (!frm.doc.requested_by && defaults.requested_by) {
    frm.doc.requested_by = defaults.requested_by;
  }
  if (!frm.doc.requested_by_name && defaults.requested_by_name) {
    frm.doc.requested_by_name = defaults.requested_by_name;
  }
  if (!frm.doc.aihr_requested_by_title && defaults.requester_title) {
    frm.doc.aihr_requested_by_title = defaults.requester_title;
  }
  if (!frm.doc.requested_by_dept && defaults.department) {
    frm.doc.requested_by_dept = defaults.department;
  }
  if (!frm.doc.department && defaults.department) {
    frm.doc.department = defaults.department;
  }
}

function getRequisitionJobTitle(doc) {
  return doc.aihr_job_title || doc.designation || "";
}

function syncRequisitionTitleFields(frm, options = {}) {
  const syncFromDesignation = Boolean(options.syncFromDesignation);
  const title = (frm.doc.aihr_job_title || "").trim();
  const designation = (frm.doc.designation || "").trim();
  const resolved = syncFromDesignation ? title || designation : title || designation;

  if (syncFromDesignation && !title && designation) {
    frm.set_value("aihr_job_title", designation);
    return;
  }

  if (title && designation !== title) {
    frm.set_value("designation", title);
  } else if (!title && designation && !syncFromDesignation) {
    frm.set_value("aihr_job_title", designation);
  } else if (!designation && title) {
    frm.set_value("designation", title);
  } else if (!title && !designation && resolved) {
    frm.set_value("aihr_job_title", resolved);
  }
}

function syncRequisitionDescriptionFields(frm, options = {}) {
  const syncFromDescription = Boolean(options.syncFromDescription);
  const roleDescription = (frm.doc.aihr_role_description_input || "").trim();
  const description = (frm.doc.description || "").trim();

  if (syncFromDescription && description && !roleDescription) {
    frm.set_value("aihr_role_description_input", description);
    return;
  }

  if (roleDescription && description !== roleDescription) {
    frm.set_value("description", roleDescription);
  } else if (!roleDescription && description && !syncFromDescription) {
    frm.set_value("aihr_role_description_input", description);
  }
}

function configureRequisitionEntryForm(frm) {
  const managerOnly = isHiringManagerOnly();

  frm.set_df_property("aihr_role_description_input", "hidden", !managerOnly);
  frm.set_df_property("aihr_role_description_input", "reqd", managerOnly ? 1 : 0);
  frm.set_df_property("description", "hidden", managerOnly ? 1 : 0);
  frm.set_df_property("description", "reqd", managerOnly ? 0 : 1);
  frm.set_df_property("requested_by", "hidden", managerOnly ? 1 : 0);
  frm.set_df_property("requested_by", "reqd", managerOnly ? 0 : 1);
  frm.set_df_property("requested_by_name", "hidden", managerOnly ? 1 : 0);
  frm.set_df_property("aihr_requested_by_title", "hidden", managerOnly ? 1 : 0);
  frm.set_df_property("requested_by_dept", "hidden", managerOnly ? 1 : 0);
  frm.set_df_property("requested_by_designation", "hidden", 1);
  frm.set_df_property("section_break_7", "hidden", managerOnly ? 1 : 0);

  syncRequisitionDescriptionFields(frm, { syncFromDescription: true });

  if (!managerOnly) {
    return;
  }

  const defaults = frm.__aihr_requisition_defaults || {};
  const requesterName = frm.doc.requested_by_name || defaults.requested_by_name || "当前登录经理";
  const requesterTitle = frm.doc.aihr_requested_by_title || defaults.requester_title || "部门经理";
  frm.set_intro(
    `需求提出人将自动带入当前登录经理：${requesterName}（${requesterTitle}）。请在当前页填写“岗位职责与要求”。`,
    "blue",
  );
}

function focusManagerDescription(frm) {
  frm.scroll_to_field("aihr_role_description_input");
  const field = frm.get_field("aihr_role_description_input");
  if (field && field.editor) {
    field.editor.set_focus();
  }
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
