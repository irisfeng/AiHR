import { AgencyBriefWorkbench } from "@/components/agency-brief-workbench";
import { AppShell, Panel, StatusPill, TagList } from "@/components/chrome";
import { JobIntakeWorkbench } from "@/components/job-intake-workbench";
import { OfferHandoffWorkbench } from "@/components/offer-handoff-workbench";
import { deriveWorkspaceSlices, getRecruitmentWorkspaceData } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function JobsPage() {
  const data = await getRecruitmentWorkspaceData();
  const { urgentJobs, activeOffers } = deriveWorkspaceSlices(data);
  const primaryJob = urgentJobs[0];

  return (
    <AppShell
      section="jobs"
      source={data.source}
      title="岗位与招聘漏斗"
      subtitle="岗位页面只保留用人经理真正会看的进度、风险和下一步。"
      actions={
        <a className="primary-button" href="#job-intake-panel">
          导入岗位需求
        </a>
      }
    >
      <section className="split-grid">
        <Panel title="重点岗位" caption="按紧急程度排序，优先消除 bottleneck。">
          {urgentJobs.length ? (
            <div className="stack-list">
              {urgentJobs.map((job) => (
                <article className="list-card" key={job.id}>
                  <div className="list-card__headline">
                    <div>
                      <h4>{job.title}</h4>
                      <p className="subtle-text">
                        {job.team} · {job.location} · HC {job.headcount}
                      </p>
                    </div>
                    <StatusPill tone={job.urgency === "critical" ? "critical" : job.urgency === "high" ? "warning" : "neutral"}>
                      {job.stage}
                    </StatusPill>
                  </div>
                  <p className="list-card__body">{job.summary}</p>
                  <div className="job-metrics">
                    <div>
                      <strong>{job.applicants}</strong>
                      <span>候选人</span>
                    </div>
                    <div>
                      <strong>{job.screened}</strong>
                      <span>已初筛</span>
                    </div>
                    <div>
                      <strong>{job.interviews}</strong>
                      <span>面试中</span>
                    </div>
                    <div>
                      <strong>{job.offers}</strong>
                      <span>Offer</span>
                    </div>
                  </div>
                  <TagList items={job.skills} />
                  <p className="subtle-text">负责人：{job.owner} · 更新时间：{job.updatedAt}</p>
                </article>
              ))}
            </div>
          ) : (
            <p className="subtle-text">还没有岗位数据。启动 API 或先录入岗位后，这里会显示优先级队列。</p>
          )}
        </Panel>

        <div className="stack-column">
          <Panel title="产品化原则" caption="岗位页不做传统 ERP 表单堆叠。">
            <div className="stack-list">
              {data.overview.priorities.map((item) => (
                <article className="note-card" key={item.title}>
                  <div className="compact-card__top">
                    <h4>{item.title}</h4>
                    <StatusPill tone="accent">{item.tag}</StatusPill>
                  </div>
                  <p>{item.detail}</p>
                </article>
              ))}
            </div>
          </Panel>

          <Panel title="目标交付" caption="这套重构不是换皮，而是减少动作成本。">
            <div className="stack-list">
              <article className="mini-stat">
                <strong>1 屏完成判断</strong>
                <span>打开岗位后，是否继续推进、卡在哪、谁负责，要在首屏说清楚。</span>
              </article>
              <article className="mini-stat">
                <strong>漏斗透明</strong>
                <span>从需求到 Offer 的转化和等待状态直接可见，不藏在子表或详情弹窗里。</span>
              </article>
              <article className="mini-stat">
                <strong>下一步明确</strong>
                <span>每个岗位只有一个首要动作，避免用户面对多个按钮犹豫。</span>
              </article>
            </div>
          </Panel>

          <Panel title="岗位 brief 预演" caption="需求单内容直接生成给猎头或招聘渠道的统一口径。">
            {primaryJob ? (
              <AgencyBriefWorkbench disabled={data.source !== "live"} job={primaryJob} />
            ) : (
              <p className="subtle-text">还没有可预演的岗位。先创建岗位或接通实时 API 后再生成 brief。</p>
            )}
          </Panel>

          <Panel title="Offer 交接工作台" caption="岗位页直接推进 Offer，不再切到另一套后台对象。">
            <OfferHandoffWorkbench
              candidates={data.candidates}
              jobs={data.jobs}
              offers={activeOffers}
              disabled={data.source !== "live"}
            />
          </Panel>

          <div id="job-intake-panel">
            <Panel title="快速录入岗位" caption="先把岗位写进持久层，漏斗和总览会自动跟着更新。">
              <JobIntakeWorkbench disabled={data.source !== "live"} />
            </Panel>
          </div>
        </div>
      </section>
    </AppShell>
  );
}
