import { AppShell, Panel, StatusPill, StatCard, TagList } from "@/components/chrome";
import { deriveWorkspaceSlices, getRecruitmentWorkspaceData } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  const data = await getRecruitmentWorkspaceData();
  const { topCandidates, urgentJobs } = deriveWorkspaceSlices(data);

  return (
    <AppShell
      section="dashboard"
      source={data.source}
      title={data.overview.title}
      subtitle={data.overview.subtitle}
      actions={
        <a className="primary-button" href="/candidates#candidate-review-panel">
          去处理经理复核
        </a>
      }
    >
      <section className="hero-card">
        <div className="hero-card__copy">
          <p className="eyebrow">Today&apos;s Focus</p>
          <h3>把用人经理真正需要看的信息推到第一屏。</h3>
          <p>
            当前重构方向只保留高频动作：岗位优先级、候选人摘要、面试反馈时效、Offer 交接状态。
          </p>
        </div>
        <div className="hero-card__actions">
          <div className="hero-blip">
            <span>待经理复核</span>
            <strong>18</strong>
          </div>
          <div className="hero-blip">
            <span>今日面试</span>
            <strong>4</strong>
          </div>
          <div className="hero-blip">
            <span>需要追反馈</span>
            <strong>2</strong>
          </div>
        </div>
      </section>

      <section className="stat-grid">
        {data.overview.stats.map((item) => (
          <StatCard key={item.label} {...item} />
        ))}
      </section>

      <section className="dashboard-grid">
        <div className="dashboard-grid__main">
          <Panel title="优先岗位" caption="直接暴露 headcount、当前阶段和下一步动作。">
            <div className="stack-list">
              {urgentJobs.slice(0, 3).map((job) => (
                <article className="list-card" key={job.id}>
                  <div className="list-card__headline">
                    <div>
                      <h4>{job.title}</h4>
                      <p className="subtle-text">
                        {job.team} · {job.location} · {job.mode}
                      </p>
                    </div>
                    <StatusPill tone={job.urgency === "critical" ? "critical" : job.urgency === "high" ? "warning" : "neutral"}>
                      {job.stage}
                    </StatusPill>
                  </div>
                  <p className="list-card__body">{job.summary}</p>
                  <div className="metric-inline">
                    <span>{job.applicants} 候选人</span>
                    <span>{job.screened} 已初筛</span>
                    <span>{job.interviews} 面试中</span>
                    <span>{job.offers} Offer</span>
                  </div>
                  <TagList items={job.skills} />
                </article>
              ))}
            </div>
          </Panel>

          <Panel title="招聘漏斗" caption="一眼看清流程哪里塞车。">
            <div className="pipeline-grid">
              {data.overview.pipeline.map((step) => (
                <article className="pipeline-step" key={step.label}>
                  <span>{step.label}</span>
                  <strong>{step.count}</strong>
                </article>
              ))}
            </div>
          </Panel>
        </div>

        <div className="dashboard-grid__aside">
          <Panel title="优先候选人" caption="把可推进的人放在最右侧，减少反复查找。">
            <div className="stack-list">
              {topCandidates.slice(0, 4).map((candidate) => (
                <article className="compact-card" key={candidate.id}>
                  <div className="compact-card__top">
                    <div>
                      <h4>{candidate.name}</h4>
                      <p className="subtle-text">{candidate.role}</p>
                    </div>
                    <div className="score-badge">{candidate.score}</div>
                  </div>
                  <p className="subtle-text">
                    {candidate.city} · {candidate.experience} · {candidate.source}
                  </p>
                  <TagList items={candidate.skills.slice(0, 4)} />
                  <p className="compact-card__note">{candidate.nextAction}</p>
                </article>
              ))}
            </div>
          </Panel>

          <Panel title="本周抓手" caption="不是功能堆砌，是把效率杠杆做重。">
            <div className="stack-list">
              {data.overview.focus.map((item) => (
                <article className="note-card" key={item.title}>
                  <h4>{item.title}</h4>
                  <p>{item.detail}</p>
                  <small>{item.owner}</small>
                </article>
              ))}
            </div>
          </Panel>
        </div>
      </section>
    </AppShell>
  );
}
