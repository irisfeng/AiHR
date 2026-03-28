import { AppShell, Panel } from "@/components/chrome";
import { HrQueueBoard } from "@/components/hr-queue-board";
import { getAgencyScorecards, getRecruitmentWorkspaceData, getWorkQueue } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function QueuePage() {
  const [workspace, queue, scorecards] = await Promise.all([
    getRecruitmentWorkspaceData(),
    getWorkQueue(),
    getAgencyScorecards(),
  ]);

  return (
    <AppShell
      section="queue"
      source={workspace.source}
      title="HR 待办工作台"
      subtitle="先处理需求、导入、复核、面试和录用收口，不先看招聘驾驶舱。"
      actions={
        <a className="primary-button" href="/jobs#requisition-intake">
          新建岗位需求
        </a>
      }
    >
      <section className="queue-hero">
        <div>
          <p className="eyebrow">Today&apos;s Workflow</p>
          <h3>默认首页只回答一个问题：我现在先处理什么。</h3>
          <p className="subtle-text">
            用人经理的自由文本需求、代理简历包、经理复核、面试反馈和录用资料，全部折成一组可执行待办。
          </p>
        </div>
        <div className="queue-hero__stats">
          <div className="hero-blip">
            <span>待整理需求</span>
            <strong>{queue.groups.find((item) => item.key === "requisition_intake")?.count ?? 0}</strong>
          </div>
          <div className="hero-blip">
            <span>待经理复核</span>
            <strong>{queue.groups.find((item) => item.key === "manager_review")?.count ?? 0}</strong>
          </div>
          <div className="hero-blip">
            <span>待约面试 / 收口</span>
            <strong>{queue.groups.find((item) => item.key === "interview_or_closeout")?.count ?? 0}</strong>
          </div>
        </div>
      </section>

      <HrQueueBoard groups={queue.groups} />

      <section className="split-grid split-grid--support">
        <Panel title="当前招聘状态" caption="只保留辅助视角，不抢首页主任务。">
          <div className="pipeline-grid">
            {workspace.overview.pipeline.map((step) => (
              <article className="pipeline-step" key={step.label}>
                <span>{step.label}</span>
                <strong>{step.count}</strong>
              </article>
            ))}
          </div>
        </Panel>

        <Panel title="代理商质量" caption="轻量事实指标，用于决定优先跟谁继续合作。">
          <div className="stack-list">
            {scorecards.slice(0, 3).map((card) => (
              <article className="note-card" key={card.agencyName}>
                <div className="compact-card__top">
                  <h4>{card.agencyName}</h4>
                  <span className="score-badge score-badge--compact">{card.rating}</span>
                </div>
                <p>
                  {card.resumeCount} 份推荐 · 经理通过率 {card.managerPassRate}% · Offer 转化率 {card.offerConversionRate}%
                </p>
              </article>
            ))}
          </div>
        </Panel>
      </section>
    </AppShell>
  );
}
