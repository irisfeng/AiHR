import { CandidateExportPanel } from "@/components/candidate-export-panel";
import { ResumeIntakeWorkbench } from "@/components/resume-intake-workbench";
import { AppShell, Panel, StatusPill, TagList } from "@/components/chrome";
import {
  getCandidateExportRows,
  getManagerReviewRequests,
  getRecruitmentWorkspaceData,
  getResumeIntakeJobs,
} from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function CandidatesPage() {
  const [data, intakeJobs, managerRequests, exportRows] = await Promise.all([
    getRecruitmentWorkspaceData(),
    getResumeIntakeJobs(),
    getManagerReviewRequests(),
    getCandidateExportRows(),
  ]);
  const recentCandidates = data.candidates.slice(0, 6);

  return (
    <AppShell
      section="candidates"
      source={data.source}
      title="简历导入与候选人总表"
      subtitle="先处理 ZIP 简历包，再跟踪待经理复核的人，最后导出全量候选人台账。"
      actions={
        <a className="primary-button" href="/manager/reviews">
          打开经理复核入口
        </a>
      }
    >
      <section className="split-grid">
        <div className="stack-column">
          <Panel title="ZIP 简历导入与 AI 初筛" caption="上传代理商发来的 ZIP 简历包，系统后台解析并自动写入候选人。">
            <ResumeIntakeWorkbench disabled={data.source !== "live"} jobs={data.jobs} recentJobs={intakeJobs} />
          </Panel>

          <Panel title="最近进入系统的候选人" caption="只看刚导入或刚推进的人，避免在大表里翻找。">
            {recentCandidates.length ? (
              <div className="stack-list">
                {recentCandidates.map((candidate) => (
                  <article className="list-card" key={candidate.id}>
                    <div className="list-card__headline">
                      <div>
                        <h4>
                          {candidate.name} · {candidate.role}
                        </h4>
                        <p className="subtle-text">
                          {candidate.city} · {candidate.experience} · {candidate.source}
                        </p>
                      </div>
                      <StatusPill tone={candidate.status === "待经理复核" ? "warning" : "accent"}>{candidate.status}</StatusPill>
                    </div>
                    <p className="list-card__body">{candidate.nextAction}</p>
                    <TagList items={candidate.skills.slice(0, 5)} />
                  </article>
                ))}
              </div>
            ) : (
              <p className="subtle-text">当前还没有候选人记录。</p>
            )}
          </Panel>
        </div>

        <div className="stack-column">
          <Panel title="待经理复核" caption="HR 在这里看是否已发给经理，以及当前卡在谁。">
            {managerRequests.length ? (
              <div className="stack-list">
                {managerRequests.map((request) => (
                  <article className="note-card" key={request.id}>
                    <div className="compact-card__top">
                      <div>
                        <h4>
                          {request.candidateName} · {request.role}
                        </h4>
                        <p className="subtle-text">{request.hrNote}</p>
                      </div>
                      <div className="score-badge score-badge--compact">{request.score}</div>
                    </div>
                    <TagList items={request.skills.slice(0, 4)} />
                    <small>等待用人经理反馈</small>
                  </article>
                ))}
              </div>
            ) : (
              <p className="subtle-text">当前没有待经理复核的候选人。</p>
            )}
          </Panel>

          <Panel title="候选人总表导出" caption="无论录用与否都保留在总表里，可用于下载、汇报与代理复盘。">
            <CandidateExportPanel disabled={data.source !== "live"} rows={exportRows} />
          </Panel>
        </div>
      </section>
    </AppShell>
  );
}
