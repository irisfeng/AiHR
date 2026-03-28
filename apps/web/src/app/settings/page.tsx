import { AppShell, Panel } from "@/components/chrome";
import { getRecruitmentWorkspaceData } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function SettingsPage() {
  const data = await getRecruitmentWorkspaceData();

  return (
    <AppShell
      section="settings"
      source={data.source}
      title="设置与模板"
      subtitle="集中放岗位模板、代理外发口径和使用说明，不让 HR 到处找文案。"
    >
      <section className="stack-column">
        <Panel title="岗位需求模板" caption="后续会在这里沉淀常用岗位模板与字段口径。">
          <p className="subtle-text">当前阶段先保留入口，避免一级导航点进去是 404。</p>
        </Panel>
        <Panel title="代理外发模板" caption="后续会沉淀标准 JD、外发摘要和回执说明。">
          <p className="subtle-text">先用岗位需求页生成的 JD 文本做统一外发。</p>
        </Panel>
      </section>
    </AppShell>
  );
}
