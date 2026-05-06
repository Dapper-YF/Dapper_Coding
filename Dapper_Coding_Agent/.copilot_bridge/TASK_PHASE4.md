# TASK_CURRENT.md — Learning Scout v4 (工作流自动化)

## 基本信息

- 触发时间：2026-04-17 16:41
- 依赖：阶段一/二/三已交付
- 执行人：GitHub Copilot
- 模式：工作流自动化（用户零干预）

---

## Context

### 当前状态

| 指标 | 数值 |
|------|------|
| 资料总数 | 约 50 条（含 embedding） |
| 核心文件 | `learning_scout.py`（约 35KB）、`dapper_coding_agent.py`（约 55KB） |
| 依赖 | `numpy>=1.26.0`、`pypdf>=4.0.0` 已安装 |
| 定时任务 | 每日 08:00 问候 + 08:05 学习资料推送 |

---

## Goal

将阶段一/二/三的能力串联成**完整自动化工作流**，实现用户零干预：

1. **失败重试机制**：API 失败自动重试 3 次，指数退避 + 随机抖动
2. **质量过滤**：自动过滤广告推广内容（关键词可配置）
3. **相似度去重**：embedding 相似度 > 0.9 视为重复，跳过入库
4. **主题分类**：LLM 自动识别主题，支持用户自定义覆盖
5. **手动触发**：新增 `POST /learning/run` 路由，供 supervisor Agent 调用
6. **稳定性提升**：连续运行 7 天无崩溃，失败率 < 5%，日志可追溯

---

## Constraints

1. **阶段一/二/三逻辑不变**：不修改已有函数的签名和行为
2. **广告过滤配置**：
   - 环境变量 `AD_KEYWORDS`：逗号分隔的关键词列表
   - 默认值：`购买，优惠，限时，特价，促销，加微信，扫码，领取`
3. **主题识别**：LLM 自动打标签（复用 `generate_summary_and_tags()`）
4. **重试策略**：3 次重试，指数退避（1s/2s/4s），随机抖动 ±0.5s
5. **相似度阈值**：0.9（标题 + 摘要 embedding 综合相似度）
6. **失败告警**：仅日志记录，不发送邮件/飞书通知
7. **手动触发 API**：`POST /learning/run`，返回执行结果摘要
8. **环境变量**：
   - `WORKFLOW_ENABLED`：工作流开关，默认 `true`
   - `AD_KEYWORDS`：广告关键词列表
   - `SIMILARITY_THRESHOLD`：相似度去重阈值，默认 `0.9`
   - `MAX_RETRY_ATTEMPTS`：最大重试次数，默认 `3`

---

## Steps

### Step 1 — 新增配置变量

```python
WORKFLOW_ENABLED = env_bool("WORKFLOW_ENABLED", True)
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.9"))
MAX_RETRY_ATTEMPTS = max(1, min(int(os.getenv("MAX_RETRY_ATTEMPTS", "3")), 5))
AD_KEYWORDS = [k.strip() for k in os.getenv("AD_KEYWORDS", "...").split(",")]
```

### Step 2 — 广告过滤函数

```python
def is_advertisement(title: str, content: str) -> bool:
    text = "{} {}".format(title, content).lower()
    for keyword in AD_KEYWORDS:
        if keyword.lower() in text:
            return True
    return False
```

### Step 3 — 相似度去重函数

```python
def check_similarity_duplicate(title: str, summary: str, threshold: float) -> bool:
    # 生成当前资料的 embedding
    # 与已有资料逐条计算余弦相似度
    # score >= threshold 返回 True（视为重复）
```

### Step 4 — 重试机制（指数退避 + 抖动）

```python
def retry_with_backoff(func, max_attempts=3, base_delay=1.0, jitter=0.5):
    # 指数退避：delay = base_delay * (2 ** (attempt - 1)) + random.uniform(-jitter, jitter)
```

### Step 5 — 主题分类（LLM 自动识别）

复用阶段三的 `generate_summary_and_tags()`，返回的 `tags` 即为主题标签。

### Step 6 — 手动触发 API

```python
@app.post("/learning/run")
def learning_run() -> dict:
    # 执行 run_learning_scout_job()
    # 返回 {status: "success/partial/failed", ...}
```

### Step 7 — 日志增强（便于 supervisor Agent 监控）

在 `run_learning_scout_job()` 中记录执行摘要：
```python
summary = {
    "fetched": 0,
    "saved": 0,
    "skipped_ads": 0,
    "skipped_duplicates": 0,
    "embeddings_generated": 0,
    "errors": [],
}
```

### Step 8 — 环境变量

```env
WORKFLOW_ENABLED=true
AD_KEYWORDS=购买，优惠，限时，特价，促销，加微信，扫码，领取
SIMILARITY_THRESHOLD=0.9
MAX_RETRY_ATTEMPTS=3
```

---

## 文件清单

| 文件路径 | 操作 | 说明 |
|---------|------|------|
| `learning_scout.py` | 修改 | 新增广告过滤/相似度去重/重试机制 |
| `dapper_coding_agent.py` | 修改 | 新增 `/learning/run` 路由 |
| `.env` | 修改 | 追加 WORKFLOW/AD/SIMILARITY/RETRY 配置 |

---

## 验收标准

- [ ] 广告内容自动跳过（标题/正文含 AD_KEYWORDS 关键词）
- [ ] 相似度 > 0.9 的资料自动跳过
- [ ] API 失败自动重试 3 次，日志显示退避延迟
- [ ] `POST /learning/run` 返回执行状态
- [ ] 工作流执行摘要记录到日志
- [ ] `WORKFLOW_ENABLED=false` 时跳过所有工作流逻辑
- [ ] 连续运行 7 天无崩溃（由 supervisor Agent 监控）
- [ ] 失败率 < 5%

---

> 阶段四完成，Learning Scout 具备完整自动化工作流能力。
