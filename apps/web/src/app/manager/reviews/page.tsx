import { CandidateReviewWorkbench } from "@/components/candidate-review-workbench";
import { AppShell, Panel, StatusPill, TagList } from "@/components/chrome";
import { getManagerReviewRequests, getRecruitmentWorkspaceData } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function ManagerReviewsPage() {
  const [data, requests] = await Promise.all([getRecruitmentWorkspaceData(), getManagerReviewRequests()]);
  const requestCandidateIds = new Set(requests.map((item) => item.candidateId));
  const reviewCandidates = data.candidates.filter(
    (candidate) => requestCandidateIds.has(candidate.id) || candidate.status === "待经理复核",
  );

  return (
    <AppShell
      section="candidates"
      source={data.source}
      title="用人经理复核入口"
      subtitle="经理只做判断：同意推进、要求补充信息、暂不推进。"
      actions={
        <a className="primary-button" href="#manager-review-workbench">
          开始复核
        </a>
      }
    >
      <section className="split-grid">
        <Panel title="待你判断的候选人" caption="只展示等待经理拍板的人，不展示整套招聘后台。">
          {requests.length ? (
            <div className="stack-list">
              {requests.map((request) => (
                <article className="note-card" key={request.id}>
                  <div className="compact-card__top">
                    <div>
                      <h4>
                        {request.candidateName} · {request.role}
                      </h4>
                      <p className="subtle-text">{request.hrNote}</p>
                    </div>
                    <StatusPill tone="warning">{request.status}</StatusPill>
                  </div>
                  <TagList items={request.skills.slice(0, 5)} />
                  <div className="metric-inline">
                    <span>匹配分 {request.score}</span>
                    <span>高亮 {request.highlights[0] ?? "待查看"}</span>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <p className="subtle-text">当前没有等待经理判断的候选人。</p>
          )}
        </Panel>

        <div className="stack-column" id="manager-review-workbench">
          <Panel title="复核动作" caption="选中候选人后，只做 3 个动作，不进入完整 ATS 工作台。">
            <CandidateReviewWorkbench
              candidates={reviewCandidates}
              disabled={data.source !== "live"}
              interviews={data.interviews}
              reviewScope="manager"
            />
          </Panel>
        </div>
      </section>
    </AppShell>
  );
}
