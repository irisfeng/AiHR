import { AppShell, Panel, StatusPill } from "@/components/chrome";
import { InterviewIntakeWorkbench } from "@/components/interview-intake-workbench";
import { deriveWorkspaceSlices, getRecruitmentWorkspaceData } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function InterviewsPage() {
  const data = await getRecruitmentWorkspaceData();
  const { pendingFeedback } = deriveWorkspaceSlices(data);

  return (
    <AppShell
      section="interviews"
      source={data.source}
      title="面试协同中心"
      subtitle="把排期、资料包和反馈时效集中在一起，减少跨群追状态。"
      actions={<button className="primary-button">安排面试</button>}
    >
      <section className="split-grid">
        <Panel title="面试日程" caption="同一屏里看清面试形式、面试官和资料包状态。">
          <div className="stack-list">
            {data.interviews.map((interview) => (
              <article className="list-card" key={interview.id}>
                <div className="list-card__headline">
                  <div>
                    <h4>
                      {interview.candidateName} · {interview.round}
                    </h4>
                    <p className="subtle-text">
                      {interview.role} · {interview.time} · {interview.mode}
                    </p>
                  </div>
                  <StatusPill tone={interview.status === "待反馈" ? "warning" : "neutral"}>{interview.status}</StatusPill>
                </div>
                <p className="list-card__body">{interview.summary}</p>
                <div className="metric-inline">
                  <span>面试官：{interview.interviewer}</span>
                  <span>资料包：{interview.packStatus}</span>
                  <span>决策窗口：{interview.decisionWindow}</span>
                </div>
              </article>
            ))}
          </div>
        </Panel>

        <div className="stack-column">
          <Panel title="待追回反馈" caption="先解决时效问题，避免候选人流失。">
            <div className="stack-list">
              {pendingFeedback.map((interview) => (
                <article className="note-card" key={interview.id}>
                  <div className="compact-card__top">
                    <h4>{interview.candidateName}</h4>
                    <StatusPill tone="warning">{interview.decisionWindow}</StatusPill>
                  </div>
                  <p>
                    {interview.round} · {interview.interviewer} · {interview.time}
                  </p>
                  <small>{interview.summary}</small>
                </article>
              ))}
            </div>
          </Panel>

          <Panel title="这页只做三件事" caption="没有必要再让用户在多个 DocType 之间来回切。">
            <div className="stack-list">
              <article className="mini-stat">
                <strong>确认面试是否准备好</strong>
                <span>人员、时间、会议链接和资料包状态首屏确认。</span>
              </article>
              <article className="mini-stat">
                <strong>收反馈是否超时</strong>
                <span>超过时限直接暴露，给协调和招聘经理一个共同视图。</span>
              </article>
              <article className="mini-stat">
                <strong>下一步是否清晰</strong>
                <span>通过、淘汰、待补充信息，必须在当日闭环，不再拖尾。</span>
              </article>
            </div>
          </Panel>

          <Panel title="快速安排面试" caption="直接把候选人、轮次和面试官写进持久层。">
            <InterviewIntakeWorkbench disabled={data.source !== "live"} />
          </Panel>
        </div>
      </section>
    </AppShell>
  );
}
