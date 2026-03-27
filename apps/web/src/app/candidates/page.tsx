import { CandidateIntakeWorkbench } from "@/components/candidate-intake-workbench";
import { ScreeningPreviewWorkbench } from "@/components/screening-preview-workbench";
import { AppShell, Panel, StatusPill, TagList } from "@/components/chrome";
import { deriveWorkspaceSlices, getCandidateTimeline, getRecruitmentWorkspaceData } from "@/lib/api";

function scoreTone(score: number): "positive" | "accent" | "warning" {
  if (score >= 85) {
    return "positive";
  }
  if (score >= 75) {
    return "accent";
  }
  return "warning";
}

export const dynamic = "force-dynamic";

export default async function CandidatesPage() {
  const data = await getRecruitmentWorkspaceData();
  const { topCandidates } = deriveWorkspaceSlices(data);
  const primaryCandidate = topCandidates[0];
  const primaryTimeline = primaryCandidate ? await getCandidateTimeline(primaryCandidate, data.interviews) : [];

  return (
    <AppShell
      section="candidates"
      source={data.source}
      title="候选人工作台"
      subtitle="候选人页默认展示证据、风险和下一步，而不是长表单。"
      actions={<button className="primary-button">导入简历 ZIP</button>}
    >
      <section className="split-grid">
        <Panel title="高优先级候选人" caption="优先展示 AI 初筛结果可直接支持决策的那批人。">
          {topCandidates.length ? (
            <div className="stack-list">
              {topCandidates.map((candidate) => (
                <article className="candidate-card" key={candidate.id}>
                  <div className="candidate-card__header">
                    <div>
                      <h4>{candidate.name}</h4>
                      <p className="subtle-text">
                        {candidate.role} · {candidate.city} · {candidate.experience}
                      </p>
                    </div>
                    <div className="candidate-card__meta">
                      <StatusPill tone={scoreTone(candidate.score)}>{candidate.status}</StatusPill>
                      <div className="score-badge">{candidate.score}</div>
                    </div>
                  </div>

                  <div className="candidate-card__body">
                    <div>
                      <p className="eyebrow">高亮证据</p>
                      <ul className="bullet-list">
                        {candidate.highlights.map((item) => (
                          <li key={item}>{item}</li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <p className="eyebrow">待确认风险</p>
                      <ul className="bullet-list bullet-list--soft">
                        {candidate.risks.map((item) => (
                          <li key={item}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  <div className="candidate-card__footer">
                    <div>
                      <TagList items={candidate.skills} />
                      <p className="subtle-text">
                        负责人：{candidate.owner} · 来源：{candidate.source}
                      </p>
                    </div>
                    <div className="action-chip">{candidate.nextAction}</div>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <p className="subtle-text">还没有候选人数据。启动 API 或导入简历后，这里会显示优先候选人。</p>
          )}
        </Panel>

        <div className="stack-column">
          <Panel title="AI 初筛预演" caption="直接调用 FastAPI，把简历字段和岗位要求变成可执行判断。">
            {primaryCandidate ? (
              <ScreeningPreviewWorkbench candidate={primaryCandidate} disabled={data.source !== "live"} />
            ) : (
              <p className="subtle-text">还没有可预演的候选人。先导入简历或接通实时 API 后再运行初筛预演。</p>
            )}
          </Panel>

          <Panel
            title={primaryCandidate ? `${primaryCandidate.name} 时间线` : "候选人时间线"}
            caption="把录入、面试安排和反馈放在一条线里，减少跨页面追状态。"
          >
            {primaryTimeline.length ? (
              <div className="timeline-feed">
                {primaryTimeline.map((event) => (
                  <article className="timeline-item" key={event.id}>
                    <div className="timeline-item__top">
                      <strong>{event.title}</strong>
                      <span>{event.happenedAt}</span>
                    </div>
                    <p>{event.detail}</p>
                    <small>执行人：{event.actor}</small>
                  </article>
                ))}
              </div>
            ) : (
              <p className="subtle-text">当前候选人还没有时间线记录。</p>
            )}
          </Panel>

          <Panel title="快速录入候选人" caption="先把新候选人写进持久层，再决定是否立即运行 AI 初筛。">
            <CandidateIntakeWorkbench disabled={data.source !== "live"} />
          </Panel>
        </div>
      </section>
    </AppShell>
  );
}
