(async () => {
  const regions = {
    heroFocus: root_element.querySelector('[data-region="hero-focus"]'),
    heroSubtitle: root_element.querySelector('[data-region="hero-subtitle"]'),
    metrics: root_element.querySelector('[data-region="metrics"]'),
    stages: root_element.querySelector('[data-region="stages"]'),
    openings: root_element.querySelector('[data-region="openings"]'),
    queue: root_element.querySelector('[data-region="queue"]'),
    candidates: root_element.querySelector('[data-region="candidates"]'),
  };

  bindActions();
  setLoadingState();
  await refreshSnapshot();

  async function refreshSnapshot() {
    try {
      const response = await frappe.call({
        method: "aihr.api.recruitment.get_hiring_hq_snapshot",
      });
      const snapshot = response.message || {};
      renderHero(snapshot);
      renderMetrics(snapshot.metrics || []);
      renderStages(snapshot.stage_counts || []);
      renderOpenings(snapshot.hot_openings || []);
      renderQueue(snapshot.focus_queue || []);
      renderCandidates(snapshot.top_candidates || []);
    } catch (error) {
      console.error(error);
      renderError();
    }
  }

  function bindActions() {
    root_element.addEventListener("click", (event) => {
      const trigger = event.target.closest("[data-action]");
      if (!trigger) {
        return;
      }

      const action = trigger.dataset.action;
      if (action === "new-requisition") {
        frappe.new_doc("Job Requisition");
      }
      if (action === "new-applicant") {
        frappe.new_doc("Job Applicant");
      }
      if (action === "open-openings") {
        window.location.assign("/app/job-opening");
      }
      if (action === "open-applicants") {
        window.location.assign("/app/job-applicant");
      }
      if (action === "open-screenings") {
        window.location.assign("/app/ai-screening");
      }
    });
  }

  function setLoadingState() {
    const loading = '<div class="aihr-hq-loading">正在同步 AIHR 招聘态势...</div>';
    regions.metrics.innerHTML = loading;
    regions.stages.innerHTML = loading;
    regions.openings.innerHTML = loading;
    regions.queue.innerHTML = loading;
    regions.candidates.innerHTML = loading;
  }

  function renderHero(snapshot) {
    const focus = snapshot.hero || {};
    regions.heroFocus.textContent = focus.title || "招聘主链路已接入";
    regions.heroSubtitle.textContent =
      focus.subtitle || "从岗位需求到候选人摘要，当前数据已在一个台面上汇总。";
  }

  function renderMetrics(metrics) {
    if (!metrics.length) {
      regions.metrics.innerHTML = emptyCard("还没有可展示的招聘指标。");
      return;
    }

    regions.metrics.innerHTML = metrics
      .map(
        (metric) => `
          <article class="aihr-hq-metric" style="--tone:${escapeHtml(metric.tone || "#0f766e")}">
            <div class="aihr-hq-metric__label">${escapeHtml(metric.label)}</div>
            <div class="aihr-hq-metric__value">${escapeHtml(metric.value)}</div>
            <div class="aihr-hq-metric__hint">${escapeHtml(metric.hint || "")}</div>
          </article>
        `
      )
      .join("");
  }

  function renderStages(stages) {
    if (!stages.length) {
      regions.stages.innerHTML = emptyCard("还没有 AI 初筛结果。");
      return;
    }

    regions.stages.innerHTML = stages
      .map(
        (stage) => `
          <article class="aihr-hq-stage" style="border-color:${escapeHtml(stage.color)}22; box-shadow: inset 0 -10px 0 ${escapeHtml(stage.color)}18;">
            <div class="aihr-hq-stage__label">${escapeHtml(stage.label)}</div>
            <div class="aihr-hq-stage__count">${escapeHtml(stage.count)}</div>
            <div class="aihr-hq-stage__hint">${escapeHtml(stage.hint || "当前候选人池分布")}</div>
          </article>
        `
      )
      .join("");
  }

  function renderOpenings(openings) {
    if (!openings.length) {
      regions.openings.innerHTML = emptyCard("当前还没有招聘中岗位。先从“新建岗位需求”开始。");
      return;
    }

    regions.openings.innerHTML = openings
      .map(
        (opening) => `
          <article class="aihr-hq-opening">
            <div class="aihr-hq-opening__head">
              <div>
                <div class="aihr-hq-opening__title">${escapeHtml(opening.title)}</div>
                <div class="aihr-hq-opening__meta">${escapeHtml(opening.meta)}</div>
              </div>
              <div class="aihr-hq-chip">${escapeHtml(opening.priority || "标准优先级")}</div>
            </div>

            <div class="aihr-hq-opening__stats">
              ${statBox("候选人", opening.total_candidates)}
              ${statBox("最高分", opening.top_score)}
              ${statBox("待处理", opening.review_queue)}
            </div>

            <div class="aihr-hq-opening__footer">
              <div class="aihr-hq-opening__meta">下一步：${escapeHtml(opening.next_action || "待确认")}</div>
              <a class="aihr-hq-inline-link" href="${escapeHtml(opening.route)}">进入岗位</a>
            </div>
          </article>
        `
      )
      .join("");
  }

  function renderQueue(items) {
    if (!items.length) {
      regions.queue.innerHTML = emptyCard("当前没有高优先级动作，说明招聘链路比较顺畅。");
      return;
    }

    regions.queue.innerHTML = items
      .map(
        (item) => `
          <article class="aihr-hq-queue-item">
            <div class="aihr-hq-queue-item__head">
              <div>
                <div class="aihr-hq-queue-item__title">${escapeHtml(item.title)}</div>
                <div class="aihr-hq-queue-item__meta">${escapeHtml(item.meta)}</div>
              </div>
              <div class="aihr-hq-chip">${escapeHtml(item.kind)}</div>
            </div>
            <div class="aihr-hq-queue-item__footer">
              <div class="aihr-hq-queue-item__meta">建议动作：${escapeHtml(item.action)}</div>
              <a class="aihr-hq-inline-link" href="${escapeHtml(item.route)}">立即处理</a>
            </div>
          </article>
        `
      )
      .join("");
  }

  function renderCandidates(candidates) {
    if (!candidates.length) {
      regions.candidates.innerHTML = emptyCard("当前还没有候选人数据。");
      return;
    }

    regions.candidates.innerHTML = candidates
      .map(
        (candidate) => `
          <article class="aihr-hq-candidate">
            <div class="aihr-hq-candidate__head">
              <div>
                <div class="aihr-hq-candidate__title">${escapeHtml(candidate.name)}</div>
                <div class="aihr-hq-candidate__meta">${escapeHtml(candidate.job_title)} · ${escapeHtml(candidate.city || "城市待补充")}</div>
              </div>
              <div class="aihr-hq-chip">${escapeHtml(candidate.status_label)}</div>
            </div>

            <div class="aihr-hq-candidate__stats">
              ${statBox("匹配分", candidate.score)}
              ${statBox("下一步", candidate.next_action_short)}
              ${statBox("来源岗位", candidate.opening_short)}
            </div>

            <div class="aihr-hq-candidate__footer">
              <div class="aihr-hq-candidate__meta">${escapeHtml(candidate.next_action || "待确认")}</div>
              <a class="aihr-hq-inline-link" href="${escapeHtml(candidate.route)}">查看摘要卡</a>
            </div>
          </article>
        `
      )
      .join("");
  }

  function renderError() {
    const message = emptyCard("招聘态势加载失败，请刷新页面或稍后重试。");
    regions.metrics.innerHTML = message;
    regions.stages.innerHTML = message;
    regions.openings.innerHTML = message;
    regions.queue.innerHTML = message;
    regions.candidates.innerHTML = message;
    regions.heroFocus.textContent = "招聘态势加载失败";
    regions.heroSubtitle.textContent = "请刷新页面或检查 AIHR 后端服务。";
  }

  function statBox(label, value) {
    return `
      <div class="aihr-hq-stat-box">
        <span>${escapeHtml(label)}</span>
        <b>${escapeHtml(value)}</b>
      </div>
    `;
  }

  function emptyCard(message) {
    return `<div class="aihr-hq-empty">${escapeHtml(message)}</div>`;
  }

  function escapeHtml(value) {
    return String(value === undefined || value === null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }
})();
