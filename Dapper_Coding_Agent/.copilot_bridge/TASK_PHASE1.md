# TASK_CURRENT.md — Learning Scout v1 (资料抓取与推送)

## 基本信息

- 触发时间：2026-04-17 12:10
- 依赖：Dapper Coding Agent 已有底座（LLM/飞书/调度/SQLite）
- 执行人：GitHub Copilot
- 模式：RSS/Atom 订阅源抓取 + LLM 摘要 + 飞书推送

---

## Context

### 核心文件

| 文件路径 | 说明 |
|---------|------|
| `dapper_coding_agent.py` | 已有 Agent 底座（可复用 LLM/飞书/调度/SQLite） |
| `requirements.txt` | 已有依赖声明 |
| `.env` | 环境变量配置（LLM/飞书 key 已配置） |
| `dapper_memory.db` | 已有 SQLite 数据库 |

### 可复用模块

| 模块 | 说明 |
|------|------|
| `init_memory_db()` | 建表逻辑（扩展新表即可） |
| `build_request_kwargs()` / `REQUEST_PROXIES` | 代理 + 超时统一出口 |
| `fetch_external_context()` | 外部上下文注入模式 |
| `run_daily_job()` 调度模式 | APScheduler cron 复用 |
| `generate_greeting()` / `generate_chat_reply()` | LLM 调用模板 |
| `get_tenant_access_token()` / `send_feishu_message()` | 飞书通道 |
| `DB_PATH` 解析逻辑 | .env 路径解析 |

---

## Goal

新增 **Learning Scout v1**，实现：

1. **配置化订阅源**：`feeds.yaml` 管理 RSS/Atom URL 列表
2. **定时抓取入库**：每天早 8 点顺带抓取所有订阅源，解析后存 SQLite
3. **LLM 自动摘要 + 打标**：对每条新内容生成 `summary`（60 字内）和 `tags`（1-3 个）
4. **每日飞书推送**：格式化为「今日学习资料」卡片，推送条数可配置
5. **完全兼容现有 `.env` 环境变量**，不破坏已有早安问候功能

---

## Constraints

1. **不破坏现有功能**：`dapper_coding_agent.py` 不修改，只新增文件
2. **Python 版本**：兼容现有 `requirements.txt` 环境
3. **新增依赖**：仅允许 `feedparser`（RSS 解析）和 `trafilatura`（正文提取）
4. **SQLite 扩展**：在 `dapper_memory.db` 中新建 `learning_scout_items` 表
5. **推送时机**：与早安问候 8:00 同批完成，数据截止到推送前一天的 24:00
6. **去重逻辑**：以 `item_url` hash 作为唯一键
7. **代理网络**：复用现有 `REQUEST_PROXIES`
8. **容错原则**：任一订阅源失败不影响其他源
9. **代码风格**：与 `dapper_coding_agent.py` 保持一致
10. **推送条数上限**：默认最多 5 条/天，可通过 `SCOUT_DAILY_LIMIT` 配置

---

## Steps

### Step 1 — 新增依赖

`requirements.txt` 末尾追加：
```
feedparser
trafilatura
```

### Step 2 — 新建 `feeds.yaml`

```yaml
feeds:
  - name: Hacker News Front Page
    url: https://hnrss.org/frontpage
    tags: [news, engineering]
    enabled: true
  - name: Python Insider
    url: https://planetpython.org/rss20.xml
    tags: [python, community]
    enabled: true
```

### Step 3 — 新建 `learning_scout.py`

实现以下函数：
- `load_feeds()` — 读取 feeds.yaml，返回 enabled 的 feed 列表
- `fetch_feed(feed_url)` — feedparser 解析 RSS/Atom
- `extract_content(url)` — trafilatura 提取正文
- `generate_summary_and_tags(title, content)` — LLM 生成摘要 + 标签（60 字/1-3 标签）
- `init_learning_scout_db()` — 新建 `learning_scout_items` 表
- `save_items(items)` — 批量 upsert，content_hash 去重
- `get_unpushed_items(limit)` — 查询未推送记录
- `format_daily_card(items)` — 飞书 interactive card JSON
- `push_daily_learning(limit)` — 查询 → 格式化 → 发送 → 标记 pushed=1
- `run_learning_scout_job()` — 完整流程

### Step 4 — 集成到 `dapper_coding_agent.py`

- 新增环境变量：`SCOUT_ENABLED=true`、`SCOUT_DAILY_LIMIT=5`
- `start_scheduler()` 中注册：`hour=8, minute=5`（早安后 5 分钟）
- `run_health_check()` 中新增：检查 feeds.yaml 可读性、trafilatura 可用性

### Step 5 — 环境变量

`.env` 新增：
```env
SCOUT_ENABLED=true
SCOUT_DAILY_LIMIT=5
```

---

## 文件清单

| 文件路径 | 操作 | 说明 |
|---------|------|------|
| `feeds.yaml` | 新增 | 订阅源配置 |
| `learning_scout.py` | 新增 | 核心逻辑 |
| `requirements.txt` | 修改 | 追加 feedparser/trafilatura |
| `dapper_coding_agent.py` | 修改 | 注册调度任务 |
| `.env` | 修改 | 追加 SCOUT 相关变量 |

---

## 验收标准

- [ ] `feeds.yaml` 可被正确解析，disabled 的源被跳过
- [ ] 重复 URL 不会重复入库（content_hash 去重）
- [ ] LLM 生成的 summary 在 60 字以内，tags 数量 1-3
- [ ] 推送卡片中每条资料有可点击标题链接
- [ ] 推送数量不超过 `SCOUT_DAILY_LIMIT`
- [ ] 单个 feed 抓取失败不影响其他 feed
- [ ] `run_health_check` 能通过（FEISHU_SIMULATE=true）
- [ ] 现有早安问候功能不受影响

---

> 阶段一完成，Learning Scout 具备基础资料抓取与推送能力。
