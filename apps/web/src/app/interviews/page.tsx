import { AppShell, Panel, StatusPill } from "@/components/chrome";
import { InterviewFeedbackWorkbench } from "@/components/interview-feedback-workbench";
import { InterviewIntakeWorkbench } from "@/components/interview-intake-workbench";
import { OfferHandoffWorkbench } from "@/components/offer-handoff-workbench";
import { deriveWorkspaceSlices, getRecruitmentWorkspaceData } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function InterviewsPage() {
  const data = await getRecruitmentWorkspaceData();
  const { pendingFeedback } = deriveWorkspaceSlices(data);

  return (
    <AppShell
      section="interviews"
      source={data.source}
      title="面试与录用收口"
      subtitle="把约面、追反馈和录用资料放在同一页闭环，避免 HR 跨页面追进度。"
      actions={
        <a className="primary-button" href="#interview-intake-panel">
          安排面试
        </a>
      }
    >
      <section className="split-grid">
        <div className="stack-column">
          <Panel title="待安排 / 进行中的面试" caption="先看还没排好或还没收回反馈的面试事项。">
            <div className="stack-list">
              {data.interviews.length ? (
                data.interviews.map((interview) => (
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
                ))
              ) : (
                <p className="subtle-text">当前没有面试记录。</p>
              )}
            </div>
          </Panel>

          <div id="interview-intake-panel">
            <Panel title="快速安排面试" caption="当经理同意推进后，HR 直接在这里确认轮次、形式、时间和面试官。">
              <InterviewIntakeWorkbench disabled={data.source !== "live"} />
            </Panel>
          </div>
        </div>

        <div className="stack-column">
          <Panel title="待追回反馈" caption="优先解决超时反馈，避免候选人空等。">
            <div className="stack-list">
              {pendingFeedback.length ? (
                pendingFeedback.map((interview) => (
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
                ))
              ) : (
                <p className="subtle-text">当前没有超时待追回的反馈。</p>
              )}
            </div>
          </Panel>

          <Panel title="回填面试反馈" caption="回填一次反馈，会同步更新候选人下一步动作和时间线。">
            <InterviewFeedbackWorkbench interviews={data.interviews} disabled={data.source !== "live"} />
          </Panel>

          <Panel title="录用收口单" caption="候选人决定录用后，直接补齐薪酬、入职和资料状态。">
            <OfferHandoffWorkbench
              candidates={data.candidates}
              disabled={data.source !== "live"}
              jobs={data.jobs}
              offers={deriveWorkspaceSlices(data).activeOffers}
            />
          </Panel>
        </div>
      </section>
    </AppShell>
  );
}
