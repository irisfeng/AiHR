import { AgencyDispatchWorkbench } from "@/components/agency-dispatch-workbench";
import { AppShell, Panel, StatusPill, TagList } from "@/components/chrome";
import { RequisitionIntakeWorkbench } from "@/components/requisition-intake-workbench";
import { getAgencyDispatches, getRecruitmentWorkspaceData, getRequisitionIntakes } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function JobsPage() {
  const [data, requisitions, dispatches] = await Promise.all([
    getRecruitmentWorkspaceData(),
    getRequisitionIntakes(),
    getAgencyDispatches(),
  ]);
  const openJobs = data.jobs.slice(0, 4);
  const draftCount = requisitions.filter((item) => ["待整理", "待确认 JD"].includes(item.status)).length;
  const pendingDispatchCount = dispatches.filter((item) => item.dispatchStatus !== "已回首份简历").length;

  return (
    <AppShell
      section="jobs"
      source={data.source}
      title="岗位需求与代理外发"
      subtitle="先收经理原话，再整理 JD，最后记录外发给谁，不再靠聊天记录和 Excel 补账。"
      actions={
        <a className="primary-button" href="#requisition-intake-panel">
          录入经理原话
        </a>
      }
    >
      <section className="split-grid">
        <div className="stack-column">
          <div id="requisition-intake-panel">
            <Panel title="岗位需求采集与 JD 生成" caption="把经理发来的原始文本贴进来，系统先抽字段，HR 再确认后生成 JD。">
              <RequisitionIntakeWorkbench disabled={data.source !== "live"} requisitions={requisitions} />
            </Panel>
          </div>

          <Panel title="当前在招岗位" caption="只保留 HR 继续推进招聘时必须知道的岗位事实。">
            {openJobs.length ? (
              <div className="stack-list">
                {openJobs.map((job) => (
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
                      <span>候选人 {job.applicants}</span>
                      <span>已初筛 {job.screened}</span>
                      <span>面试中 {job.interviews}</span>
                      <span>Offer {job.offers}</span>
                    </div>
                    <TagList items={job.skills.slice(0, 6)} />
                  </article>
                ))}
              </div>
            ) : (
              <p className="subtle-text">还没有在招岗位。生成第一条 JD 后，这里会自动出现。</p>
            )}
          </Panel>
        </div>

        <div className="stack-column">
          <Panel title="代理外发记录" caption="记录这份 JD 发给了谁、何时发送、当前是否已回首批简历。">
            <AgencyDispatchWorkbench disabled={data.source !== "live"} dispatches={dispatches} jobs={data.jobs} />
          </Panel>

          <Panel title="当前抓手" caption="这页只追 3 个关键动作，不再堆大盘。">
            <div className="stack-list">
              <article className="mini-stat">
                <strong>{draftCount}</strong>
                <span>待确认 JD 的岗位需求单</span>
              </article>
              <article className="mini-stat">
                <strong>{pendingDispatchCount}</strong>
                <span>待继续跟进回简历的代理外发记录</span>
              </article>
              <article className="mini-stat">
                <strong>{data.jobs.filter((item) => item.stage === "代理寻访中").length}</strong>
                <span>已进入代理寻访中的岗位</span>
              </article>
            </div>
          </Panel>
        </div>
      </section>
    </AppShell>
  );
}
