(function () {
  const DESK_ENTRY = "/app";
  const LOGIN_VARIANTS = {
    ".for-login": {
      title: "欢迎回到 AIHR",
      subtitle: "进入岗位需求、简历导入、AI 初筛、面试协同与 Offer 管理，保持招聘主线清晰可见。",
    },
    ".for-email-login": {
      title: "使用邮箱登录",
      subtitle: "如果当前站点启用了邮箱登录，可以继续使用邮箱和密码进入 AIHR。",
    },
    ".for-login-with-email-link": {
      title: "通过邮件链接登录",
      subtitle: "如果你更适合使用免密入口，可以通过邮箱链接完成验证并进入 AIHR。",
    },
    ".for-forgot": {
      title: "重置登录密码",
      subtitle: "输入你的邮箱后，系统会发送密码重置邮件，帮助你安全地回到 AIHR。",
    },
  };

  function initAIHRLoginShell() {
    if (window.location.pathname.startsWith("/app")) {
      return;
    }

    const userId = getCookie("user_id");
    const isGuest = !userId || userId === "Guest";

    if (!window.location.pathname.startsWith("/login")) {
      redirectTo(isGuest ? `/login?redirect-to=${encodeURIComponent(DESK_ENTRY)}` : DESK_ENTRY);
      return;
    }

    if (!isGuest) {
      redirectTo(DESK_ENTRY);
      return;
    }

    document.body.classList.add("aihr-login-page");
    document.title = "AIHR 登录";

    Object.keys(LOGIN_VARIANTS).forEach((selector) => enhanceLoginSection(selector));
    bindLoginSectionLayoutSync();
  }

  function enhanceLoginSection(selector) {
    const section = document.querySelector(selector);
    if (!section || section.querySelector(".aihr-login-hero")) {
      return;
    }

    const variant = LOGIN_VARIANTS[selector];
    if (!variant) {
      return;
    }

    const head = section.querySelector(".page-card-head");
    const card = section.querySelector(".login-content.page-card");
    if (!head || !card) {
      return;
    }

    const panel = document.createElement("section");
    panel.className = "aihr-login-panel";

    head.classList.add("aihr-login-intro");
    const title = head.querySelector("h4");
    if (title) {
      title.textContent = variant.title;
    }

    if (!head.querySelector(".aihr-login-eyebrow")) {
      const eyebrow = document.createElement("div");
      eyebrow.className = "aihr-login-eyebrow";
      eyebrow.textContent = "AIHR 招聘系统";
      head.insertBefore(eyebrow, head.firstChild);
    }

    if (!head.querySelector(".aihr-login-subtitle")) {
      const subtitle = document.createElement("p");
      subtitle.className = "aihr-login-subtitle";
      subtitle.textContent = variant.subtitle;
      head.appendChild(subtitle);
    }

    panel.appendChild(head);
    panel.appendChild(card);
    section.prepend(panel);

    const hero = document.createElement("aside");
    hero.className = "aihr-login-hero";
    hero.innerHTML = `
      <div class="aihr-login-kicker">AIHR 招聘后台</div>
      <div class="aihr-login-hero-title">让招聘流程回到清晰、稳定的工作界面。</div>
      <div class="aihr-login-hero-copy">
        岗位需求、ZIP 简历导入、AI 初筛、面试反馈与 Offer 管理统一收口在同一条主线上。
        AI 负责整理、摘要与提醒，人保留判断与确认。
      </div>
      <div class="aihr-login-points">
        <div class="aihr-login-point">优先服务 HR 与用人经理的日常推进，而不是展示 ERP 模块清单。</div>
        <div class="aihr-login-point">支持供应商简历包导入、候选人建档、AI 初筛与面试协同。</div>
      </div>
      <div class="aihr-login-metrics">
        <div class="aihr-login-metric">
          <div class="aihr-login-metric-label">当前主线</div>
          <div class="aihr-login-metric-value">招聘流程 MVP</div>
        </div>
        <div class="aihr-login-metric">
          <div class="aihr-login-metric-label">默认体验</div>
          <div class="aihr-login-metric-value">中文优先</div>
        </div>
        <div class="aihr-login-metric">
          <div class="aihr-login-metric-label">协同方式</div>
          <div class="aihr-login-metric-value">AI 初筛与协同</div>
        </div>
      </div>
    `;

    section.appendChild(hero);
  }

  function redirectTo(target) {
    if (window.location.pathname + window.location.search === target) {
      return;
    }
    window.location.replace(target);
  }

  function getCookie(name) {
    const prefix = `${name}=`;
    return document.cookie
      .split(";")
      .map((item) => item.trim())
      .find((item) => item.startsWith(prefix))
      ?.slice(prefix.length);
  }

  function bindLoginSectionLayoutSync() {
    const selectors = Object.keys(LOGIN_VARIANTS);
    const sync = () => {
      selectors.forEach((selector) => {
        const section = document.querySelector(selector);
        if (!section) {
          return;
        }

        const visible = section.style.display !== "none" && getComputedStyle(section).display !== "none";
        if (visible) {
          section.style.display = "grid";
        }
      });
    };

    sync();
    window.addEventListener("hashchange", () => window.requestAnimationFrame(sync));

    selectors.forEach((selector) => {
      const section = document.querySelector(selector);
      if (!section) {
        return;
      }

      const observer = new MutationObserver(() => window.requestAnimationFrame(sync));
      observer.observe(section, {
        attributes: true,
        attributeFilter: ["style", "class"],
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initAIHRLoginShell, { once: true });
  } else {
    initAIHRLoginShell();
  }
})();
