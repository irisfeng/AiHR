(function () {
  const AIHR_ALLOWED_WORKSPACES = new Set(["AIHR 招聘总览", "AIHR 用人经理中心", "AIHR 面试协同中心"]);
  const AIHR_WORKSPACE_ROUTES = {
    "AIHR 招聘总览": "/app/aihr-hiring-hq",
    "AIHR 用人经理中心": "/app/aihr-manager-review",
    "AIHR 面试协同中心": "/app/aihr-interview-desk",
  };
  const AIHR_WORKSPACE_ACCESS = {
    "AIHR 招聘总览": ["HR User", "HR Manager", "System Manager"],
    "AIHR 用人经理中心": ["AIHR Hiring Manager", "HR Manager", "System Manager"],
    "AIHR 面试协同中心": ["Interviewer", "HR User", "HR Manager", "System Manager"],
  };
  const AIHR_WORKSPACE_LINKS = [
    {
      label: "AIHR 招聘总览",
      route: "/app/aihr-hiring-hq",
      meta: "招聘主线",
    },
    {
      label: "AIHR 用人经理中心",
      route: "/app/aihr-manager-review",
      meta: "经理复核",
    },
    {
      label: "AIHR 面试协同中心",
      route: "/app/aihr-interview-desk",
      meta: "面试推进",
    },
  ];
  const AIHR_WORKSPACE_PATH_REDIRECTS = {
    "/app/aihr-招聘总览": "/app/aihr-hiring-hq",
    "/app/aihr-用人经理中心": "/app/aihr-manager-review",
    "/app/aihr-面试协同中心": "/app/aihr-interview-desk",
  };
  const AIHR_BLOCKED_DESK_PREFIXES = ["/app/user-profile", "/app/leaderboard"];
  const AIHR_WORKSPACE_SLUGS = {
    "AIHR 招聘总览": "aihr-招聘总览",
    "AIHR 用人经理中心": "aihr-用人经理中心",
    "AIHR 面试协同中心": "aihr-面试协同中心",
  };
  const AIHR_ROUTE_STRING_REDIRECTS = {
    "Workspaces/AIHR 招聘作战台": "Workspaces/AIHR 招聘总览",
    "Workspaces/AIHR 用人经理台": "Workspaces/AIHR 用人经理中心",
    "Workspaces/AIHR 面试官台": "Workspaces/AIHR 面试协同中心",
  };
  const AIHR_WORKSPACE_HISTORY_REDIRECTS = {
    "AIHR 招聘作战台": "AIHR 招聘总览",
    "AIHR 用人经理台": "AIHR 用人经理中心",
    "AIHR 面试官台": "AIHR 面试协同中心",
  };
  const AIHR_BLOCKED_HISTORY_ROUTES = new Set(["Workspaces/HR"]);
  const AIHR_VISIBLE_LABELS = {
    "AIHR 招聘作战台": "AIHR 招聘总览",
    "AIHR 用人经理台": "AIHR 用人经理中心",
    "AIHR 面试官台": "AIHR 面试协同中心",
    "AIHR Hiring HQ": "AIHR 招聘总览",
    "AIHR Manager Review": "AIHR 用人经理中心",
    "AIHR Interview Desk": "AIHR 面试协同中心",
    "AIHR Interview Control Room": "AIHR 面试概览",
    "AIHR Feedback Console": "AIHR 反馈概览",
    "AIHR Offer Handoff": "AIHR 录用概览",
    "AIHR Onboarding Hub": "AIHR 入职概览",
    HR: "人力资源",
    "招聘作战台": "招聘总览",
    "岗位战情": "岗位概况",
    "标准作战路径": "标准推进路径",
    "岗位作战卡": "岗位概览卡",
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
    Workspace: "工作台",
    Workspaces: "工作台",
    Pending: "待处理",
    "On Hold": "已搁置",
    Filled: "已招满",
    Cancelled: "已取消",
    Save: "保存",
  };

  function initAIHRDeskShell() {
    document.body.classList.add("aihr-desk");
    patchRouterForAIHRWorkspaces();
    sanitizeSearchHistory();
    redirectWorkspaceAliasRoute();
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
    patchRouterForAIHRWorkspaces();
    sanitizeSearchHistory();
    redirectWorkspaceAliasRoute();
    removeWebsiteMenuEntry();
    injectBrandLabel();
    filterWorkspaceSidebar();
    translateVisibleLabels();
  }

  function redirectWorkspaceAliasRoute() {
    const normalizedPath = decodeURIComponent(window.location.pathname || "");
    const target = normalizeAihrUrl(normalizedPath);
    if (target && window.location.pathname !== target) {
      window.location.replace(target);
    }
  }

  function patchRouterForAIHRWorkspaces() {
    if (!window.frappe || !frappe.router) {
      return;
    }

    registerWorkspaceAliases();

    if (!frappe.router.__aihr_make_url_patched) {
      const originalMakeUrl = frappe.router.make_url.bind(frappe.router);
      frappe.router.make_url = function patchedMakeUrl(params) {
        const directUrl = getDirectWorkspaceUrl(params);
        if (directUrl) {
          return directUrl;
        }

        const generated = originalMakeUrl(params);
        return normalizeAihrUrl(generated) || generated;
      };
      frappe.router.__aihr_make_url_patched = true;
    }

    if (!frappe.router.__aihr_push_state_patched) {
      const originalPushState = frappe.router.push_state.bind(frappe.router);
      frappe.router.push_state = function patchedPushState(url) {
        return originalPushState(normalizeAihrUrl(url) || url);
      };
      frappe.router.__aihr_push_state_patched = true;
    }
  }

  function registerWorkspaceAliases() {
    if (!window.frappe || !frappe.router || !frappe.workspaces) {
      return;
    }

    Object.entries(AIHR_WORKSPACE_ROUTES).forEach(([label, route]) => {
      const stableSlug = route.replace("/app/", "");
      const aliasSlug = AIHR_WORKSPACE_SLUGS[label];
      const workspace = frappe.workspaces[stableSlug];
      if (workspace && aliasSlug && !frappe.workspaces[aliasSlug]) {
        frappe.workspaces[aliasSlug] = workspace;
      }
    });
  }

  function getDirectWorkspaceUrl(params) {
    if (!params) {
      return getPreferredDeskEntry();
    }

    const route = Array.isArray(params) ? params.flat() : [params];
    if (!route.length) {
      return getPreferredDeskEntry();
    }

    if (route[0] === "Workspaces" && AIHR_WORKSPACE_ROUTES[route[1]]) {
      return AIHR_WORKSPACE_ROUTES[route[1]];
    }

    if (route.length === 1) {
      return normalizeAihrUrl(`/app/${String(route[0]).replace(/^\/app\//, "")}`);
    }

    return null;
  }

  function normalizeAihrUrl(url) {
    if (!url) {
      return null;
    }

    const normalized = decodeURIComponent(String(url).trim());
    if (normalized === "/app") {
      return getPreferredDeskEntry();
    }
    if (AIHR_BLOCKED_DESK_PREFIXES.some((prefix) => normalized.startsWith(prefix))) {
      return getPreferredDeskEntry();
    }
    const redirected = AIHR_WORKSPACE_PATH_REDIRECTS[normalized] || null;
    const current = redirected || normalized;
    return userCanAccessPath(current) ? redirected : getPreferredDeskEntry();
  }

  function getPreferredDeskEntry() {
    const roles = getCurrentUserRoles();
    if (roles.has("HR Manager") || roles.has("HR User") || roles.has("System Manager")) {
      return AIHR_WORKSPACE_ROUTES["AIHR 招聘总览"];
    }
    if (roles.has("AIHR Hiring Manager")) {
      return AIHR_WORKSPACE_ROUTES["AIHR 用人经理中心"];
    }
    if (roles.has("Interviewer")) {
      return AIHR_WORKSPACE_ROUTES["AIHR 面试协同中心"];
    }
    return AIHR_WORKSPACE_ROUTES["AIHR 招聘总览"];
  }

  function getCurrentUserRoles() {
    const roles = frappe?.boot?.user?.roles || frappe?.user_roles || [];
    return new Set(Array.isArray(roles) ? roles : []);
  }

  function userCanAccessPath(path) {
    const routeEntry = Object.entries(AIHR_WORKSPACE_ROUTES).find(([, route]) => route === path);
    if (!routeEntry) {
      return true;
    }
    const [label] = routeEntry;
    const allowedRoles = AIHR_WORKSPACE_ACCESS[label] || [];
    const roles = getCurrentUserRoles();
    return allowedRoles.some((role) => roles.has(role));
  }

  function sanitizeSearchHistory() {
    if (!window.frappe) {
      return;
    }

    if (Array.isArray(frappe.route_history)) {
      frappe.route_history = dedupeBy(
        frappe.route_history.map(normalizeRouteArray).filter(Boolean),
        (item) => JSON.stringify(item)
      );
    }

    if (frappe.boot && Array.isArray(frappe.boot.frequently_visited_links)) {
      frappe.boot.frequently_visited_links = dedupeBy(
        frappe.boot.frequently_visited_links
          .map((link) => normalizeFrequentLink(link))
          .filter(Boolean),
        (item) => item.route
      );
    }
  }

  function normalizeRouteArray(route) {
    if (!Array.isArray(route) || !route.length) {
      return route;
    }

    if (route[0] === "Workspaces" && route[1]) {
      const label = AIHR_WORKSPACE_HISTORY_REDIRECTS[route[1]] || route[1];
      return ["Workspaces", label, ...route.slice(2)];
    }

    return route;
  }

  function normalizeFrequentLink(link) {
    if (!link || !link.route) {
      return null;
    }

    const route = AIHR_ROUTE_STRING_REDIRECTS[link.route] || link.route;
    if (!route || shouldHideFrequentRoute(route)) {
      return null;
    }

    return { ...link, route };
  }

  function shouldHideFrequentRoute(route) {
    return AIHR_BLOCKED_HISTORY_ROUTES.has(route) || route.startsWith("Workspaces/");
  }

  function dedupeBy(items, selector) {
    const seen = new Set();
    return items.filter((item) => {
      const key = selector(item);
      if (seen.has(key)) {
        return false;
      }
      seen.add(key);
      return true;
    });
  }

  function injectBrandLabel() {
    const home = document.querySelector(".navbar-home");
    if (!home) {
      return;
    }

    home.setAttribute("href", AIHR_WORKSPACE_ROUTES["AIHR 招聘总览"]);
    document.querySelectorAll('a[href="/app"], .btn-home').forEach((node) => {
      node.setAttribute("href", AIHR_WORKSPACE_ROUTES["AIHR 招聘总览"]);
    });

    if (home.querySelector(".aihr-brand-text")) {
      return;
    }

    const label = document.createElement("span");
    label.className = "aihr-brand-text";
    label.textContent = "AIHR";
    home.appendChild(label);
  }

  function removeWebsiteMenuEntry() {
    if (window.frappe?.boot?.navbar_settings?.settings_dropdown) {
      frappe.boot.navbar_settings.settings_dropdown = frappe.boot.navbar_settings.settings_dropdown.filter(
        (item) => item?.item_label !== "View Website" && item?.item_label !== "查看网站"
      );
    }

    if (window.frappe?.ui?.toolbar?.view_website) {
      frappe.ui.toolbar.view_website = () => {
        window.location.assign(AIHR_WORKSPACE_ROUTES["AIHR 招聘总览"]);
      };
    }

    document
      .querySelectorAll(".dropdown-navbar-user [data-label='View Website'], .dropdown-navbar-user .dropdown-item")
      .forEach((node) => {
        const text = (node.textContent || "").trim();
        const href = node.getAttribute?.("href") || "";
        if (
          text === "查看网站" ||
          text === "View Website" ||
          text === "我的资料" ||
          text === "My Profile" ||
          text === "User Profile" ||
          text === "排行榜" ||
          text === "Leaderboard" ||
          AIHR_BLOCKED_DESK_PREFIXES.some((prefix) => href.startsWith(prefix))
        ) {
          node.remove();
        }
      });
  }

  function filterWorkspaceSidebar() {
    document.querySelectorAll(".desk-sidebar").forEach((sidebar) => {
      const wrapper = sidebar.closest(".layout-side-section");
      if (wrapper) {
        wrapper.classList.add("aihr-sidebar");
      }

      if (renderCustomWorkspaceSidebar(sidebar)) {
        return;
      }

      let visibleSectionCount = 0;

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
        if (visibleItems.length > 0) {
          visibleSectionCount += 1;
        }

        const title = section.querySelector(".section-title");
        if (title && visibleItems.length > 0 && title.textContent.trim() === "Public") {
          title.textContent = "AIHR 导航";
        }
      });

      sidebar.classList.toggle("aihr-single-section", visibleSectionCount <= 1);
    });
  }

  function renderCustomWorkspaceSidebar(sidebar) {
    if (!sidebar || !isAihrWorkspacePath()) {
      sidebar?.classList.remove("aihr-workspace-sidebar");
      return false;
    }

    const currentPath = normalizeAihrUrl(decodeURIComponent(window.location.pathname || "")) || decodeURIComponent(window.location.pathname || "");
    const signature = AIHR_WORKSPACE_LINKS.map((item) => item.label).join("|");

    if (sidebar.dataset.aihrWorkspaceSignature !== signature || !sidebar.querySelector(".aihr-workspace-nav")) {
      sidebar.innerHTML = `
        <div class="aihr-workspace-nav">
          <div class="aihr-workspace-nav-title">AIHR 导航</div>
          <div class="aihr-workspace-nav-list">
            ${AIHR_WORKSPACE_LINKS.map(
              (item) => `
                <a class="aihr-workspace-link" data-route="${item.route}" href="${item.route}">
                  <span class="aihr-workspace-link-label">${item.label}</span>
                  <span class="aihr-workspace-link-meta">${item.meta}</span>
                </a>
              `
            ).join("")}
          </div>
        </div>
      `;
      sidebar.dataset.aihrWorkspaceSignature = signature;
    }

    sidebar.classList.add("aihr-workspace-sidebar", "aihr-single-section");
    Array.from(sidebar.children).forEach((child) => {
      if (child.classList.contains("aihr-workspace-nav")) {
        child.style.display = "";
        child.removeAttribute("aria-hidden");
        return;
      }

      child.classList.add("aihr-hidden-section");
      child.style.display = "none";
      child.setAttribute("aria-hidden", "true");
    });

    sidebar.querySelectorAll(".aihr-workspace-link").forEach((link) => {
      link.classList.toggle("is-active", link.getAttribute("data-route") === currentPath);
    });

    return true;
  }

  function isAihrWorkspacePath() {
    const currentPath = normalizeAihrUrl(decodeURIComponent(window.location.pathname || "")) || decodeURIComponent(window.location.pathname || "");
    return Object.values(AIHR_WORKSPACE_ROUTES).includes(currentPath);
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
      .filter((source) => source.length >= 4)
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
