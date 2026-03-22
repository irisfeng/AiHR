# MinerU PDF 解析说明

AIHR 当前已支持将 `PDF` 简历优先交给 MinerU 官方 API 解析，并在失败时自动回退到本地解析。

## 当前策略

- 单个 `PDF` 附件：优先走 MinerU，失败后回退本地 `pypdf`
- `ZIP` 简历包中的多个 `PDF`：优先走 MinerU 批量上传与批量结果轮询，失败文件自动回退本地解析
- `DOCX / DOC / TXT`：继续走本地解析

## 环境变量

推荐做法是先复制环境变量模板：

```bash
cp .env.example .env.local
```

然后至少设置：

```dotenv
AIHR_MINERU_API_TOKEN="你的 MinerU Token"
```

可选项：

```dotenv
AIHR_MINERU_USER_TOKEN="可选的用户标识"
AIHR_MINERU_MODEL_VERSION="vlm"
AIHR_MINERU_LANGUAGE="ch"
AIHR_MINERU_ENABLE_OCR="1"
AIHR_MINERU_BATCH_SIZE="50"
AIHR_MINERU_REQUEST_TIMEOUT_SECONDS="60"
AIHR_MINERU_POLL_INTERVAL_SECONDS="2"
AIHR_MINERU_POLL_TIMEOUT_SECONDS="180"
```

## 说明

- 未配置 `AIHR_MINERU_API_TOKEN` 时，系统不会报错，而是继续走本地解析
- `./scripts/start_dev_site.sh` 会自动读取项目根目录下的 `.env` 与 `.env.local`
- MinerU 返回的是结果压缩包，AIHR 会自动提取其中的 `full.md`，再转成可用于简历字段识别的文本
- 当前接入方式已经适配供应商 `ZIP` 批量简历导入场景
