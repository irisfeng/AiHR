# AI 语义筛选与面试助手

AIHR 当前已经支持两层 AI 能力：

1. `PDF` 简历解析：优先走 MinerU
2. 候选人语义筛选与面试助手：走可配置的大模型接口

## 当前启用逻辑

- 未配置 `AIHR_LLM_API_KEY`：
  - `AI 初筛` 继续使用启发式评分
  - `面试资料包` 和 `面试反馈摘要` 使用本地模板逻辑
- 已配置 `AIHR_LLM_API_KEY`：
  - `AI 初筛` 升级为语义筛选
  - `Interview` 页面生成更完整的面试资料包
  - `Interview Feedback` 会生成更自然的 AI 总结、建议和录用推荐

## 推荐配置

先复制环境变量模板：

```bash
cp .env.example .env.local
```

然后在 `.env.local` 中填写：

```dotenv
AIHR_LLM_API_KEY="你的大模型 API Key"
AIHR_LLM_BASE_URL="https://api.openai.com/v1"
AIHR_LLM_MODEL="gpt-5-mini"
AIHR_LLM_TEMPERATURE="0.2"
AIHR_LLM_REQUEST_TIMEOUT_SECONDS="60"
```

如果你使用的是 OpenAI 兼容接口，也可以把 `AIHR_LLM_BASE_URL` 指向兼容网关地址。

## 生效范围

### 1. AI 初筛

入口：

- `招聘中岗位 -> 批量 AI 初筛`
- `候选人档案 -> 运行 AI 初筛`

输出：

- 匹配分
- 建议状态
- 匹配技能
- 缺失技能
- AI 摘要
- 优势
- 风险点
- 建议追问问题

### 2. 面试资料包

入口：

- `Interview -> 生成 / 刷新面试资料包`

输出：

- 候选人判断
- 本轮关注重点
- 建议追问问题
- 面试观察点
- 面后决策提示

### 3. 面试反馈总结

入口：

- `Interview Feedback -> 应用面试结论`

输出：

- AI 总结
- 一句话面试结论
- 建议下一步动作
- 录用推荐

## 说明

- 当前实现是“可配置增强层”，不会破坏现有招聘链路
- 大模型接口异常时，系统会自动回退到现有启发式/模板逻辑
- 真实候选人简历属于敏感数据，生产环境接入外部模型前建议先完成数据合规评估
