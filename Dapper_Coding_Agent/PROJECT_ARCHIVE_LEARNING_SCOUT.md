# PROJECT_ARCHIVE_LEARNING_SCOUT.md

**项目名称**：Learning Scout v2
**归档时间**：2026-04-26
**项目路径**：`E:\Study\Dapper_Coding`

---

## 项目概述

**目标**：将 Learning Scout 从"功能堆砌"重构为"真正的智能体"

**核心特性**：
- 统一记忆层（用户画像 + 学习进度 + 阅读历史）
- Tech Digest 模块（采集 → 阅读 → 整理 → 推送）
- 反馈闭环（点击/忽略 → 更新偏好）
- 企业微信 + 飞书双渠道推送
- 多用户支持

---

## 项目结构

```
E:\Study\Dapper_Coding\
├── memory.py                    # 统一记忆层（17个核心函数）
├── tech_digest.py               # Tech Digest 核心模块
├── weixin_client.py            # 企业微信应用客户端
├── dapper_coding_agent.py       # 主服务（FastAPI）
├── learning_scout.py            # Learning Scout 主逻辑
├── feeds.yaml                   # RSS 订阅源配置
├── dapper_memory.db             # SQLite 数据库
├── .env                         # 环境变量配置
└── .copilot_bridge\            # 任务文档
    ├── TASK_A1.md              # Phase A1 记录
    ├── TASK_A2.md              # Phase A2 记录
    ├── TASK_A3.md              # Phase A3 记录
    ├── TASK_A4.md              # Phase A4 记录
    ├── TASK_A5.md              # Phase A5 记录
    ├── TASK_A6.md              # Phase A6 记录
    └── TASK_A7.md              # Phase A7 记录
```

---

## 已完成的 Phase

| Phase | 内容 | 状态 | 关键交付物 |
|-------|------|------|-----------|
| A1 | 需求梳理 + 架构讨论 | ✅ 完成 | 架构设计文档 |
| A2 | 架构设计 + 核心模块实现 | ✅ 完成 | memory.py, tech_digest.py |
| A3 | 数据库迁移 | ✅ 完成 | 3 个新表 |
| A4 | 定时任务集成 | ✅ 完成 | run_digest_job(), 08:10 定时 |
| A5 | 反馈闭环 + 偏好更新 | ✅ 完成 | /digest/feedback API |
| A6 | 多用户支持 | ✅ 完成 | 用户管理 API |
| A7 | 企业微信深度集成 | ✅ 完成 | WeiXinClient, Card 推送 |

---

## 核心模块说明

### 1. memory.py - 统一记忆层

**数据模型**：
- `UserProfile` - 用户画像
- `LearningProgress` - 学习进度
- `ReadingRecord` - 阅读记录
- `DigestRecord` - Digest 推送记录

**核心函数**：
```python
get_profile(user_id)              # 获取用户画像
update_profile(user_id, **kwargs) # 更新用户画像
register_user(user_id, ...)      # 注册用户
set_digest_enabled(user_id, bool) # 启用/禁用 Digest
get_all_active_users()           # 获取所有活跃用户
update_热度权重(user_id, topic, delta) # 更新热度权重
```

### 2. tech_digest.py - Tech Digest 核心

**流程**：采集 → 筛选 → 整理 → 推送 → 学习

**核心函数**：
```python
run_tech_digest(user_id)         # 执行完整 Digest 流程
run_daily_digest_batch()         # 批量为所有用户执行
collect_articles()               # 采集 RSS 文章
collect_tavily_articles()        # 采集 Tavily 文章
filter_relevant_articles()       # 筛选相关文章
digest_articles()                # 生成 Digest
send_digest_card()               # 发送 Card 消息
push_to_weixin()                 # 推送到企业微信
learn_from_feedback()            # 从反馈学习
```

### 3. weixin_client.py - 企业微信客户端

**类**：`WeiXinClient`

**方法**：
```python
send_text(content)               # 发送文本
send_markdown(content)           # 发送 Markdown
send_news(articles)              # 发送图文
send_textcard(title, desc, url)  # 发送卡片
```

### 4. dapper_coding_agent.py - API 服务

**端口**：默认 8000

**API 接口**：

| 接口 | 方法 | 说明 |
|------|------|------|
| `/digest/run` | POST | 手动触发 Tech Digest |
| `/digest/feedback` | POST | 记录反馈 |
| `/users/register` | POST | 注册用户 |
| `/users/set-digest` | POST | 启用/禁用 Digest |
| `/users/list` | GET | 列出所有用户 |
| `/users/{user_id}` | DELETE | 删除用户 |
| `/weixin/callback` | POST/GET | 企业微信回调 |

---

## 数据库表结构

### user_profiles
```sql
CREATE TABLE user_profiles (
    user_id TEXT PRIMARY KEY,
    关注领域 TEXT DEFAULT '',
    难度偏好 TEXT DEFAULT '入门',
    阅读深度偏好 TEXT DEFAULT '中等',
    热度权重 TEXT DEFAULT '{}',
    weixin_webhook TEXT DEFAULT '',
    digest_enabled INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
```

### learning_progress
```sql
CREATE TABLE learning_progress (
    user_id TEXT PRIMARY KEY,
    direction TEXT DEFAULT '',
    total_days INTEGER DEFAULT 56,
    current_day INTEGER DEFAULT 1,
    stage_summary TEXT DEFAULT '',
    started_at TEXT NOT NULL
)
```

### reading_history
```sql
CREATE TABLE reading_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    item_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    feedback_text TEXT,
    created_at TEXT NOT NULL
)
```

---

## 企业微信配置

```bash
WEIXIN_CORP_ID=YOUR_WEIXIN_CORP_ID
WEIXIN_AGENT_ID=1000002
WEIXIN_CORP_SECRET=<env>
```

---

## RSS 订阅源（feeds.yaml）

1. 机器之心 - AI 前沿
2. 量子位 - AI 科技
3. 36氪 - 创业科技
4. AI前线 - 人工智能
5. 知乎 - AI 话题
6. SegmentFault - 技术社区

---

## 定时任务

| 时间 | 任务 |
|------|------|
| 08:00 | 早安问候 |
| 08:05 | Learning Scout |
| 08:10 | Tech Digest（AI 简报推送）|

---

## 测试清单

### 基础测试

```bash
# 1. 语法检查
python -m py_compile memory.py
python -m py_compile tech_digest.py
python -m py_compile weixin_client.py
python -m py_compile dapper_coding_agent.py

# 2. 启动服务
python dapper_coding_agent.py

# 3. 健康检查
curl http://localhost:8000/health

# 4. 测试 Tech Digest
curl -X POST http://localhost:8000/digest/run \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_user"}'

# 5. 测试用户注册
curl -X POST http://localhost:8000/users/register \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_user", "关注领域": "AI,NLP", "难度偏好": "入门"}'

# 6. 测试列出用户
curl http://localhost:8000/users/list

# 7. 测试反馈
curl -X POST http://localhost:8000/digest/feedback \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_user", "item_id": 1, "action": "click", "feedback_text": ""}'
```

---

## 已知限制

1. **企业微信回调**需要公网可访问的服务器 URL
2. **Tavily API** 需要有效的 API Key
3. **多用户模式**下，每个用户需要单独注册

---

## 下一步方向（未实现）

1. **企业微信深度集成** - 完整的 click-through 追踪
2. **用户画像持久化** - 更完整的用户偏好管理
3. **Digest 内容优化** - 基于反馈自动调整内容
4. **飞书深度集成** - 富文本消息、交互按钮

---

## 参与成员

- **Architect/Commander**：龙虾 Architect（Principal Architect）
- **Supervisor**：The Supervisor（Quality Gatekeeper）

---

*归档完成时间：2026-04-26 16:52 GMT+8*
