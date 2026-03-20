# AIHR 本地开发环境接入

本文档面向 AIHR 项目的开发同学，目标是在最短时间内把 Frappe + ERPNext + HRMS + AIHR 联调起来。

## 推荐方式

推荐使用官方 `frappe_docker` 作为开发环境底座，再把当前项目作为自定义 app 挂载进去。

原因：

- 与 Frappe 官方推荐方式一致
- 容器环境更稳定
- 后续从开发过渡到测试环境更顺滑
- 对 `aihr` 这种自定义 app 更友好

## 前置要求

- Docker Desktop 或 Docker Engine
- Git
- 本地可访问 GitHub
- 当前仓库已克隆到本地

## 第一步：拉取 Frappe Docker 参考环境

可以直接使用项目内脚本：

```bash
./scripts/bootstrap_frappe_docker.sh
```

这个脚本会：

- 在项目目录下创建 `.frappe_docker/`
- 拉取官方 `frappe_docker`
- 将当前项目里的 [apps.json](/Users/tony/Documents/GitHub/aihr/infra/apps.json) 复制到开发目录

## 第二步：按官方方式初始化开发环境

进入 Frappe Docker 目录：

```bash
cd .frappe_docker
```

推荐使用官方开发模式，而不是 `pwd.yml` 快速试跑模式。原因是 `pwd.yml` 适合快速体验，但不适合挂自定义 app。

按官方文档，开发环境主要依赖：

- `development/installer.py`
- `development/apps.json`

你们需要确认 `development/apps.json` 中至少包含：

- ERPNext
- HRMS

当前项目已经准备好了这个文件来源：

- [apps.json](/Users/tony/Documents/GitHub/aihr/infra/apps.json)

## 第三步：创建 bench 和站点

在开发容器或开发 shell 中执行官方安装器，例如：

```bash
cd /workspace/development
python installer.py --apps-json apps.json --bench-name frappe-bench --site-name development.localhost
```

完成后，bench 目录通常会在：

```bash
development/frappe-bench
```

## 第四步：安装当前 AIHR app

在 bench 所在环境中执行：

```bash
BENCH_DIR=/path/to/frappe-bench \
SITE_NAME=development.localhost \
./scripts/install_local_app.sh
```

如果你已经进入 bench 所在容器，也可以只设置：

```bash
BENCH_DIR=/workspace/development/frappe-bench \
SITE_NAME=development.localhost \
/workspace/aihr/scripts/install_local_app.sh
```

## 第五步：验证联调结果

至少验证以下对象：

- `Job Requisition`
- `Job Opening`
- `Job Applicant`
- `Interview`
- `Job Offer`
- `AI Screening`

重点确认：

- 自定义字段是否出现
- `AI Screening` 是否可创建
- `bench build --app aihr` 后页面是否正常

## 第六步：灌入演示数据

先启动本地站点服务：

```bash
./scripts/start_dev_site.sh
```

默认访问地址：

```text
http://development.localhost:18000
```

当前本地联调默认管理员账号：

```text
Administrator / AIHRAdmin!2026
```

然后用 AIHR 提供的 demo 数据入口快速建立一条招聘主流程：

```bash
./scripts/seed_demo_site.sh
```

也可以直接在 bench 中调用：

```python
frappe.call("aihr.api.demo.seed_demo_recruitment_data", company="Your Company")
```

这个入口会创建：

- 演示用岗位需求
- 演示用岗位
- 演示用候选人
- 候选人 AI 初筛摘要

## 常见建议

- 开发阶段优先先跑通“站点可见 + 字段可见 + demo 数据可灌入”
- 不要一开始就追求复杂前端页面
- 先在标准 DocType 和标准表单里验证业务流程，再做更好的界面
- 简历 PDF 解析先以“能提取文本并生成摘要”为准，不急着追求极致准确率

## 当前最小联调闭环

`Job Requisition -> Job Opening -> Job Applicant -> AI Screening`

只要这条闭环先通了，后面的 `Interview` 和 `Job Offer` 就会轻松很多。
