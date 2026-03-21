(function () {
  const AIHR_ALLOWED_WORKSPACES = new Set(["AIHR 招聘作战台", "AIHR 用人经理台", "AIHR 面试官台"]);
  const AIHR_WORKSPACE_ROUTES = {
    "AIHR 招聘作战台": "/app/aihr-hiring-hq",
    "AIHR 用人经理台": "/app/aihr-manager-review",
    "AIHR 面试官台": "/app/aihr-interview-desk",
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

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initAIHRDeskShell, { once: true });
  } else {
    initAIHRDeskShell();
  }
})();
