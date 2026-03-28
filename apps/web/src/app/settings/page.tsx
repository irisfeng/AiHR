import { AgencyScorecardPanel } from "@/components/agency-scorecard-panel";
import { AppShell, Panel } from "@/components/chrome";
import { getAgencyScorecards, getRecruitmentWorkspaceData } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function SettingsPage() {
  const [data, scorecards] = await Promise.all([getRecruitmentWorkspaceData(), getAgencyScorecards()]);

  return (
    <AppShell
      section="settings"
      source={data.source}
      title="设置与模板"
      subtitle="集中放岗位模板、代理外发口径和使用说明，不让 HR 到处找文案。"
    >
      <section className="split-grid">
        <Panel title="代理商质量评估" caption="基于事实数据看每家代理的简历量、推进率和录用结果。">
          <AgencyScorecardPanel scorecards={scorecards} />
        </Panel>
        <div className="stack-column">
          <Panel title="岗位需求模板" caption="这页只沉淀真正会反复复用的文字口径。">
            <div className="stack-list">
              <article className="mini-stat">
                <strong>经理原话</strong>
                <span>先贴原始需求，再由系统抽字段，避免 HR 反复转述。</span>
              </article>
              <article className="mini-stat">
                <strong>JD 文本</strong>
                <span>在岗位需求页确认后生成，对外发代理统一口径。</span>
              </article>
              <article className="mini-stat">
                <strong>录用收口</strong>
                <span>薪酬待遇、体检和无犯罪记录都在面试与录用页收口。</span>
              </article>
            </div>
          </Panel>
          <Panel title="使用手册交付" caption="开发落地后会提供完整手册，不让团队靠口头传授。">
            <p className="subtle-text">手册会覆盖 HR 日常流程、经理复核入口、ZIP/PDF 上传、异常处理、候选人总表导出和代理商评估解释。</p>
          </Panel>
        </div>
      </section>
    </AppShell>
  );
}
