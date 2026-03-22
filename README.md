# AIHR

AIHR 是一个基于 Frappe HR 二次开发的 AI 化招聘与人力运营 MVP。

当前版本聚焦国内公司的招聘主流程，目标是先把岗位需求、候选人推进、面试协同、Offer 与入职交接从 Excel 和人工搬运中收口到一个系统里，并用 AI 减少摘要、整理、提醒和记录这些重复工作。

## 当前范围

当前 MVP 主链路：

`岗位需求 -> 招聘中岗位 -> 候选人录入 -> AI 初筛 -> 面试协同 -> 面试反馈 -> Offer -> 入职交接`

当前更适合这样理解：

- 这是一个招聘优先的 AIHR MVP，不是完整 HRMS
- 当前已经可以本地试用和演示招聘主链路
- 员工主档自动创建、薪酬建档与 Payroll 正式联动仍在后续范围内

## 快速开始

### 本地访问

- 地址：`http://development.localhost:18000`
- 用户名：`Administrator`
- 密码：`AIHRAdmin!2026`

### 本地启动

如果已经按项目约定准备好 Docker Desktop，可按下面顺序启动：

```bash
./scripts/bootstrap_frappe_docker.sh
./scripts/start_dev_site.sh
./scripts/seed_demo_site.sh
```

如需让 `PDF` 简历优先走 MinerU 官方 API 解析，推荐先复制环境变量模板：

```bash
cp .env.example .env.local
```

然后在 `.env.local` 中填写：

```bash
AIHR_MINERU_API_TOKEN="你的 MinerU Token"
```

`./scripts/start_dev_site.sh` 会自动读取项目根目录下的 `.env` 和 `.env.local`，并把 `AIHR_` / `MINERU_` 变量传入容器。

如果是将当前 app 安装到已有 Frappe bench，可使用：

```bash
./scripts/install_local_app.sh
```

## 基本使用

建议从 `AIHR 招聘总览` 开始使用。

日常最基本的操作顺序：

1. 新建 `岗位需求单`
2. 创建 `招聘中岗位`
3. 在 `招聘中岗位` 页面点击 `导入简历压缩包`
4. 上传供应商提供的 ZIP 简历包，系统自动解析并生成候选人档案
5. 运行或自动生成 `AI 初筛`
6. 在 `面试安排`、`面试反馈`、`Offer 管理`、`入职交接` 中继续推进

如果要单独验证“中文简历材料 -> 解析 -> AI 摘要”这条能力，可执行：

```bash
python3 scripts/validate_chinese_materials.py
```

当前系统内的主要角色入口：

- `AIHR 招聘总览`
- `AIHR 用人经理中心`
- `AIHR 面试协同中心`

## 文档

- 测试操作手册：[docs/test-guide.md](/Users/tony/Documents/GitHub/aihr/docs/test-guide.md)
- 项目北极星：[docs/north-star.md](/Users/tony/Documents/GitHub/aihr/docs/north-star.md)
- 使用手册：[docs/user-manual.md](/Users/tony/Documents/GitHub/aihr/docs/user-manual.md)
- 简历导入与优化方案：[docs/resume-intake-plan.md](/Users/tony/Documents/GitHub/aihr/docs/resume-intake-plan.md)
- MinerU PDF 解析说明：[docs/mineru-api.md](/Users/tony/Documents/GitHub/aihr/docs/mineru-api.md)
- 本地开发说明：[docs/development-setup.md](/Users/tony/Documents/GitHub/aihr/docs/development-setup.md)
- 国际化状态：[docs/i18n-status.md](/Users/tony/Documents/GitHub/aihr/docs/i18n-status.md)

## 说明

- 当前仓库以 `Frappe + ERPNext + HRMS + aihr` 的方式运行
- 当前界面已做 AIHR OEM 化和中文优先收口
- 如果用于对外商业化分发，建议尽早评估上游 GPL 许可证边界
