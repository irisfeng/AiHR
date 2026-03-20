# AIHR

AIHR 是一个基于 Frappe HR 二次开发的 AI 化招聘与人力运营 MVP 项目，目标不是一次性做完整 HRMS，而是优先解决国内公司在人力招聘流程中最耗时、最重复、最依赖 Excel 和人工沟通的那部分工作。

项目北极星见：[docs/north-star.md](/Users/tony/Documents/GitHub/aihr/docs/north-star.md)。
使用手册见：[docs/user-manual.md](/Users/tony/Documents/GitHub/aihr/docs/user-manual.md)。
国际化状态说明见：[docs/i18n-status.md](/Users/tony/Documents/GitHub/aihr/docs/i18n-status.md)。

当前版本按“1 周可交付 MVP”思路收敛，核心目标非常明确：

- 替代 Excel 维护岗位需求、候选人状态和面试进度
- 把 PDF 简历自动结构化，减少 HR 手工录入
- 给用人经理直接输出 AI 候选人摘要，而不是只丢原始简历
- 把面试、Offer、入职、薪酬建档交接串成一条记录主线

## 项目定位

AIHR 不是大而全的人力资源系统一期，而是一个“招聘作战台 + 生命周期入口”。

一期重点围绕这条主流程：

`岗位需求 -> 岗位发布 -> 简历接收 -> AI 初筛 -> 面试协同 -> Offer -> 入职交接 -> 薪酬建档准备`

适合当前典型场景：

- 部门经理提招聘需求
- HR 补充岗位职责、薪酬区间、工作地点和班次
- 发给第三方招聘代理或渠道发布
- 收到候选人 PDF 简历后做结构化录入和初筛
- 与用人经理协同推进一面、二面、反馈和 Offer

## 当前仓库包含什么

- 一个 Frappe 自定义应用骨架：`aihr`
- 1 周 MVP 范围说明和实施文档：`docs/`
- 面向招聘流程的自定义字段安装逻辑
- 一个新的 `AI Screening` DocType，用于保存 AI 候选人摘要卡
- 纯 Python 的简历解析与启发式筛选服务
- 一个本地安装脚本，方便把当前项目挂载进现有 Frappe bench

## 已落地的能力

当前代码已经覆盖了 MVP 的第一层骨架：

- `Job Requisition` 扩展字段
  - 招聘优先级
  - 工作地点
  - 工作模式
  - 工作时间
  - 薪资区间
  - 必备技能 / 加分项
  - 代理发布说明
- `Job Opening` 扩展字段
  - 招聘执行负责人
  - 渠道策略
  - 下一个动作
  - 代理发布包
- `Job Applicant` 扩展字段
  - 简历文本缓存
  - AI 状态
  - 匹配分数
  - 候选人城市
  - 工作年限
  - 下一个动作和跟进时间
- `Interview` 扩展字段
  - 面试方式
  - 跟进负责人
  - 反馈截止时间
  - 面试官资料包
- `Job Offer` 扩展字段
  - 入职负责人
  - 薪酬交接状态
  - 薪酬备注
- `AI Screening` 新对象
  - 候选人匹配分
  - 优势
  - 风险点
  - 建议追问问题
  - 简历解析 JSON
  - 筛选结果 JSON

## 为什么按 1 周 MVP 收敛

这个项目的一期目标不是做全生命周期 HR 系统，而是先把最痛的招聘执行链条数字化、结构化、AI 化。

1 周内的“成功标准”应该是：

- 用人经理可以提交结构化岗位需求
- HR 可以快速生成标准岗位说明和代理发布包
- 简历可以上传并自动抽取关键信息
- 每个候选人都有一张 AI 摘要卡，经理能更快做初筛判断
- 面试、Offer、入职、薪酬建档交接不再靠 Excel 追踪

## 建议技术方案

- 平台底座：Frappe + ERPNext + HRMS
- 公司定制逻辑：当前仓库 `aihr`
- 开发环境：MariaDB + Redis + 官方 Frappe Docker 开发方式

`infra/apps.json` 当前采用 `version-15` 作为初始化基线，主要是为了降低 1 周 MVP 的搭建风险。后续如果你们确认升级到更新版本，可以在稳定后再迁移。

## 快速开始

1. 先准备一个可运行的 Frappe 开发环境，并安装 ERPNext 与 HRMS。
2. 将当前仓库挂载到 bench 的 `apps/` 目录下。
3. 运行安装脚本：`scripts/install_local_app.sh`
4. 在目标站点执行 `install-app` 或 `migrate`
5. 优先配置和验证以下对象：
   - `Job Requisition`
   - `Job Applicant`
   - `AI Screening`

如果使用当前仓库推荐的本地 Docker 联调方式，可以继续执行：

1. 准备 Frappe Docker 参考目录：`./scripts/bootstrap_frappe_docker.sh`
2. 在开发容器中安装 app：`BENCH_DIR=/workspace/development/frappe-bench SITE_NAME=development.localhost ./scripts/install_local_app.sh`
3. 启动站点服务：`./scripts/start_dev_site.sh`
4. 灌入演示数据：`./scripts/seed_demo_site.sh`
5. 浏览器访问：`http://development.localhost:18000`

当前本地联调默认管理员账号：

- 用户名：`Administrator`
- 密码：`AIHRAdmin!2026`

重点参考：

- `docs/week-1-mvp.md`
- `docs/data-model.md`
- `docs/development-setup.md`
- `scripts/install_local_app.sh`
- `scripts/start_dev_site.sh`
- `scripts/seed_demo_site.sh`
- `scripts/preview_screening.py`

## 本地预览能力

在 Frappe 环境还没完全启动前，也可以先用本地脚本预览候选人摘要能力：

```bash
python3 scripts/preview_screening.py \
  --requirements-file /path/to/requirements.txt \
  --resume-file /path/to/resume.pdf \
  --preferred-city 上海
```

这个脚本会输出：

- 简历解析结果
- 候选人匹配分
- 优势与风险
- 建议面试追问问题

## 当前不在一期范围内

以下内容不建议在 1 周 MVP 内硬上：

- 复杂薪资核算
- 考勤、请假、报销
- 绩效、培训、员工全生命周期细化管理
- 各大招聘网站深度 API 对接
- 电话语音机器人
- 面向外部候选人的完整门户

## 许可证说明

Frappe HR 使用 `GPL-3.0` 许可证。如果 AIHR 未来不只是内部使用，而是要对外分发、商业化交付，建议尽早做法务评估和许可证边界确认。
