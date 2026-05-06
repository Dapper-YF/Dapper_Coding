# TASK_A2.md — Phase A2：智能体架构重构设计 + 核心模块实现

## 基本信息

- 阶段编号：A2（设计 + 编码）
- 触发时间：2026-04-26
- 执行人：Principal Architect（直接执行）
- 状态：✅ 完成

---

## 完成内容

### 1. 架构设计文档

**文件**：`E:\Study\Dapper_Coding\.copilot_bridge\TASK_A2.md`

包含：
- 统一记忆层设计
- Tech Digest 模块流程设计
- 简报格式设计
- 企业微信接入方案
- 反馈闭环逻辑
- 数据库表设计

### 2. memory.py - 统一记忆层

**文件**：`E:\Study\Dapper_Coding\memory.py`

**提供功能**：

| 函数 | 功能 |
|------|------|
| `init_memory_db()` | 初始化数据库表 |
| `get_profile(user_id)` | 获取用户画像 |
| `update_profile(user_id, **fields)` | 更新用户画像 |
| `update_热度权重(user_id, 领域, delta)` | 更新领域热度 |
| `get_learning_progress(user_id)` | 获取学习进度 |
| `advance_learning_day(user_id)` | 推进学习进度 |
| `record_reading(user_id, item_id, action, feedback_text)` | 记录阅读行为 |
| `get_reading_history(user_id, days)` | 获取阅读历史 |
| `get_user_clicked_items(user_id)` | 获取点击过的文章 |
| `record_digest(user_id, push_date, title, content, source_articles)` | 记录 Digest 推送 |
| `get_latest_digest(user_id)` | 获取最新 Digest |
| `get_all_active_users()` | 获取所有活跃用户 |

### 3. tech_digest.py - Tech Digest 核心模块

**文件**：`E:\Study\Dapper_Coding\tech_digest.py`

**流程**：

```
采集（RSS + Tavily）→ 筛选（根据用户偏好）→ 整理（LLM 生成简报）→ 推送 → 闭环
```

**提供功能**：

| 函数 | 功能 |
|------|------|
| `collect_articles()` | 从 RSS 订阅源采集文章 |
| `collect_tavily_articles()` | 使用 Tavily 搜索最新资讯 |
| `filter_relevant_articles(articles, user_id)` | 根据用户偏好筛选文章 |
| `digest_articles(articles, user_id)` | LLM 整理成一篇简报 |
| `push_to_weixin(content)` | 推送到企业微信 |
| `push_to_feishu(open_id, content)` | 推送到飞书 |
| `learn_from_feedback(user_id, action, feedback_text)` | 根据反馈更新偏好 |
| `run_tech_digest(user_id)` | 执行全流程 |
| `run_daily_digest_batch()` | 批量为所有用户执行 |

---

## 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      Agent Core                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐           │
│   │  Memory  │◄──►│   LLM    │◄──►│  Tools   │           │
│   │  记忆层  │    │  推理中枢 │    │  工具集  │           │
│   └──────────┘    └──────────┘    └──────────┘           │
│                                                             │
│   ┌──────────────────────────────────────────────────┐     │
│   │  memory.py (统一记忆层)                          │     │
│   │  • user_profiles • digest_history              │     │
│   │  • reading_history • learning_progress          │     │
│   └──────────────────────────────────────────────────┘     │
│                                                             │
│   ┌──────────────────────────────────────────────────┐     │
│   │  tech_digest.py (Tech Digest 模块)               │     │
│   │  • 采集 (RSS + Tavily)                           │     │
│   │  • 筛选 (用户偏好匹配)                           │     │
│   │  • 整理 (LLM 生成简报)                          │     │
│   │  • 推送 (企业微信 + 飞书)                       │     │
│   │  • 闭环 (反馈更新偏好)                          │     │
│   └──────────────────────────────────────────────────┘     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Tech Digest 简报格式

```
【今日 AI 速报】2026-04-26

🤖 今日头条
OpenAI 发布 GPT-5，在多个基准测试中超越人类专家水平...

📰 重要进展
• Google DeepMind 提出新架构，训练效率提升 40%
• Meta 开源新模型，支持 100+ 语言的统一表示
• 斯坦福发布 2026 AI Index 报告

📚 深度阅读推荐
《Transformer 的最新演进》
推荐理由：与你学习的 NLP 方向高度相关

💬 今日小结
今天 AI 圈最火的方向是"高效推理"...
```

---

## 环境变量

```env
# 企业微信（新增）
WEIXIN_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx

# Tech Digest 配置（新增）
DIGEST_TAVILY_ENABLED=true
DIGEST_DAILY_LIMIT=10
DIGEST_MAX_ARTICLES=10
DIGEST_CONTENT_MAX_LENGTH=1000
LLM_DIGEST_TEMPERATURE=0.3
LLM_DIGEST_MAX_TOKENS=1500
```

---

## 下一步

**Phase A3**：数据库迁移（已完成并入本阶段）

**Phase A4**：集成到定时任务
- 在 `dapper_coding_agent.py` 中添加 Tech Digest 定时任务
- 设置每天 08:05 执行

---

_Architect 执行签名：🦞_
