(function () {
  function initAIHRLoginShell() {
    if (!window.location.pathname.startsWith("/login")) {
      return;
    }

    document.body.classList.add("aihr-login-page");
    document.title = "AIHR 登录";

    enhanceLoginSection(".for-login");
    enhanceLoginSection(".for-email-login");
  }

  function enhanceLoginSection(selector) {
    const section = document.querySelector(selector);
    if (!section || section.querySelector(".aihr-login-hero")) {
      return;
    }

    const hero = document.createElement("aside");
    hero.className = "aihr-login-hero";
    hero.innerHTML = `
      <div class="aihr-login-kicker">AIHR OEM Shell</div>
      <div class="aihr-login-hero-title">让招聘作战台看起来就像 AIHR 本身。</div>
      <div class="aihr-login-hero-copy">
        用 Frappe 承载流程和数据，用 AIHR 承载品牌、协同和智能化体验。HR 团队打开系统，
        看到的应该是招聘主链路，而不是 ERP 模块清单。
      </div>
      <div class="aihr-login-points">
        <div class="aihr-login-point">岗位需求、候选人、面试反馈、Offer 与入职交接全部在一条主线上推进。</div>
        <div class="aihr-login-point">AI 优先负责摘要、整理、提醒和协同，HR 保留关键判断与确认。</div>
        <div class="aihr-login-point">后台保持低代码扩展能力，前台逐步长成你们自己的 AIHR 产品。</div>
      </div>
      <div class="aihr-login-metrics">
        <div class="aihr-login-metric">
          <div class="aihr-login-metric-label">当前主线</div>
          <div class="aihr-login-metric-value">招聘 MVP</div>
        </div>
        <div class="aihr-login-metric">
          <div class="aihr-login-metric-label">默认语言</div>
          <div class="aihr-login-metric-value">中文优先</div>
        </div>
        <div class="aihr-login-metric">
          <div class="aihr-login-metric-label">交互目标</div>
          <div class="aihr-login-metric-value">AI 协同</div>
        </div>
      </div>
    `;

    const card = section.querySelector(".login-content.page-card");
    if (card) {
      card.before(hero);
    } else {
      section.appendChild(hero);
    }

    const title = section.querySelector(".page-card-head h4");
    if (title && title.textContent.includes("Login")) {
      title.textContent = "登录到 AIHR";
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initAIHRLoginShell, { once: true });
  } else {
    initAIHRLoginShell();
  }
})();
