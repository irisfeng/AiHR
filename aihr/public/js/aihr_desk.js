(function () {
  const AIHR_ALLOWED_WORKSPACES = new Set(["AIHR 招聘作战台", "AIHR 用人经理台", "AIHR 面试官台"]);
  const AIHR_WORKSPACE_ROUTES = {
    "AIHR 招聘作战台": "/app/aihr-hiring-hq",
    "AIHR 用人经理台": "/app/aihr-manager-review",
    "AIHR 面试官台": "/app/aihr-interview-desk",
  };
  const AIHR_VISIBLE_LABELS = {
    "AIHR Hiring HQ": "AIHR 招聘作战台",
    "AIHR Manager Review": "AIHR 用人经理台",
    "AIHR Interview Desk": "AIHR 面试官台",
    HR: "人力资源",
    "AI Screening": "AI 初筛",
    "New AI Screening": "新建 AI 初筛",
    "Add AI Screening": "新增 AI 初筛",
    "Job Requisition": "岗位需求单",
    "New Job Requisition": "新建岗位需求单",
    "Add Job Requisition": "新增岗位需求单",
    "Job Opening": "招聘中岗位",
    "New Job Opening": "新建招聘中岗位",
    "Add Job Opening": "新增招聘中岗位",
    "Job Applicant": "候选人档案",
    "New Job Applicant": "新建候选人档案",
    "Add Job Applicant": "新增候选人档案",
    Interview: "面试安排",
    "New Interview": "新建面试安排",
    "Add Interview": "新增面试安排",
    "Interview Feedback": "面试反馈",
    "New Interview Feedback": "新建面试反馈",
    "Add Interview Feedback": "新增面试反馈",
    "Job Offer": "Offer 管理",
    "New Job Offer": "新建 Offer",
    "Add Job Offer": "新增 Offer",
    "Employee Onboarding": "入职交接",
    "New Employee Onboarding": "新建入职交接",
    "Add Employee Onboarding": "新增入职交接",
    Employee: "员工档案",
    "List View": "列表视图",
    "Filter By": "过滤条件",
    "Assigned To": "已分配给",
    "Created By": "创建人",
    "Last Updated On": "最后更新时间",
    "Edit Filters": "编辑过滤器",
    "Show Tags": "显示标签",
    "Save Filter": "保存筛选条件",
    "Filter Name": "过滤器名称",
    "Clear all filters": "清空全部过滤条件",
    "Liked by me": "我的收藏",
    "Not Saved": "尚未保存",
    "Job Description": "职位描述",
    "Naming Series": "编号规则",
    Timelines: "时间安排",
    Details: "详细信息",
    ID: "编号",
    Designation: "职位",
    "No. of Positions": "招聘人数",
    "No of. Positions": "招聘人数",
    "Posting Date": "发布日期",
    "Begin typing for results.": "开始输入以查看结果。",
    "Expected Compensation": "预期薪酬",
    "Requested By": "需求提出人",
    "Expected By": "期望到岗日期",
    "Open & Approved": "已审批开放",
    Pending: "待处理",
    "On Hold": "已搁置",
    Filled: "已招满",
    Cancelled: "已取消",
    Save: "保存",
  };

  function initAIHRDeskShell() {
    document.body.classList.add("aihr-desk");
    enhanceDeskShell();

    if (window.frappe && frappe.router && !window.__aihr_desk_router_bound) {
      frappe.router.on("change", scheduleEnhance);
      window.__aihr_desk_router_bound = true;
    }

    if (!window.__aihr_desk_page_change_bound) {
      document.addEventListener("page-change", scheduleEnhance);
      window.__aihr_desk_page_change_bound = true;
    }

    if (!window.__aihr_desk_observer) {
      const observer = new MutationObserver(scheduleEnhance);
      observer.observe(document.body, { childList: true, subtree: true });
      window.__aihr_desk_observer = observer;
    }
  }

  function scheduleEnhance() {
    window.requestAnimationFrame(enhanceDeskShell);
    window.setTimeout(enhanceDeskShell, 140);
  }

  function enhanceDeskShell() {
    document.body.classList.add("aihr-desk");
    injectBrandLabel();
    filterWorkspaceSidebar();
    translateVisibleLabels();
  }

  function injectBrandLabel() {
    const home = document.querySelector(".navbar-home");
    if (!home || home.querySelector(".aihr-brand-text")) {
      return;
    }

    const label = document.createElement("span");
    label.className = "aihr-brand-text";
    label.textContent = "AIHR";
    home.appendChild(label);
  }

  function filterWorkspaceSidebar() {
    document.querySelectorAll(".desk-sidebar").forEach((sidebar) => {
      const wrapper = sidebar.closest(".layout-side-section");
      if (wrapper) {
        wrapper.classList.add("aihr-sidebar");
      }

      sidebar.querySelectorAll(".sidebar-item-container").forEach((item) => {
        const label = item.querySelector(".sidebar-item-label")?.textContent?.trim() || "";
        const shouldShow = AIHR_ALLOWED_WORKSPACES.has(label);
        item.classList.toggle("aihr-hidden-nav", !shouldShow);

        const link = item.querySelector("a");
        if (shouldShow && link && AIHR_WORKSPACE_ROUTES[label]) {
          link.setAttribute("href", AIHR_WORKSPACE_ROUTES[label]);
        }
      });

      sidebar.querySelectorAll(".standard-sidebar-section").forEach((section) => {
        const visibleItems = Array.from(section.querySelectorAll(".sidebar-item-container")).filter(
          (item) => !item.classList.contains("aihr-hidden-nav")
        );

        section.classList.toggle("aihr-hidden-section", visibleItems.length === 0);

        const title = section.querySelector(".section-title");
        if (title && visibleItems.length > 0 && title.textContent.trim() === "Public") {
          title.textContent = "AIHR 工作台";
        }
      });
    });
  }

  function translateVisibleLabels() {
    document.querySelectorAll("a, span, div, button, label, li, p, h1, h2, h3, h4, h5, h6, small, option").forEach((node) => {
      if (!node.children.length && node.textContent) {
        const translated = translateValue(node.textContent);
        if (translated && node.textContent !== translated) {
          node.textContent = translated;
        }
      }
    });

    document.querySelectorAll("[title], [aria-label], [data-original-title], input[placeholder], textarea[placeholder]").forEach((node) => {
      translateAttribute(node, "title");
      translateAttribute(node, "aria-label");
      translateAttribute(node, "data-original-title");
      translateAttribute(node, "placeholder");
    });

    const translatedTitle = translateValue(document.title);
    if (translatedTitle && document.title !== translatedTitle) {
      document.title = translatedTitle;
    }
  }

  function translateExact(value) {
    const text = (value || "").trim();
    return AIHR_VISIBLE_LABELS[text];
  }

  function translateValue(value) {
    const exact = translateExact(value);
    if (exact) {
      return exact;
    }

    let translated = value || "";
    Object.keys(AIHR_VISIBLE_LABELS)
      .sort((left, right) => right.length - left.length)
      .forEach((source) => {
        if (translated.includes(source)) {
          translated = translated.split(source).join(AIHR_VISIBLE_LABELS[source]);
        }
      });

    return translated === value ? null : translated;
  }

  function translateAttribute(node, attribute) {
    const current = node.getAttribute(attribute);
    const translated = translateValue(current);
    if (translated && current !== translated) {
      node.setAttribute(attribute, translated);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initAIHRDeskShell, { once: true });
  } else {
    initAIHRDeskShell();
  }
})();
