# Phase 17: 多用户支持 - 架构设计与实现方案

## 1. 背景与现状分析

### 1.1 当前用户身份体系

经过代码调研，当前系统中存在**两个并行的用户身份体系**，未做统一映射：

| 身份维度 | 飞书 (Feishu) | 企业微信 (WeChat) |
|---------|---------------|-------------------|
| **用户标识来源** | `event.sender.sender_id.open_id` | `xml.FromUserName` |
| **标识字段** | `open_id` | `FromUserName` / `ActualUserName` |
| **代码中变量名** | `open_id` | `user_id` / `actual_user` / `from_user` |
| **memory.py 存储字段** | 未使用 memory.py（只用 `greetings_history` 按 `open_id` 存） | 使用 `user_id` 存储 |
| **dialogue_manager** | 未调用 | 通过 `LearningAgent.process_message` 调用 |

### 1.2 飞书 & 企微消息流的根本差异

```
飞书:
  feishu_webhook → handle_feishu_message
    ├── onboarding 分流
    ├── 搜索分流
    ├── RAG 问答
    └── generate_chat_reply (LLM 直接生成)
    (不走 LearningAgent，不使用 dialogue_manager)

企微:
  weixin_callback → LearningAgent.process_message(user_id, channel, text)
    ├── dialogue_manager (记录对话)
    ├── quiz_engine (检测待答测验)
    ├── intent classification
    ├── teach_with_context / Sogou 搜索
    └── dialogue_manager (记录回复)
```

### 1.3 关键问题清单

| 编号 | 问题 | 严重性 |
|------|------|--------|
| Q1 | **飞书用户不走 LearningAgent**，没有对话管理、意图分类、quiz 检测 | 🔴 高 |
| Q2 | **飞书 `open_id` 和企微 `FromUserName` 不互通**，同一个真实用户跨渠道没有关联 | 🔴 高 |
| Q3 | **全局 SQLite 无锁机制**，并发消息可能产生数据竞争 | 🟡 中 |
| Q4 | **memory.py 的 `user_id` vs `greetings_history` 的 `open_id`** 指向不同含义 | 🟡 中 |
| Q5 | **对话没有过期清理机制**（dialogue_manager 有 cleanup_old_sessions 但未被调度） | 🟢 低 |

---

## 2. 架构设计方案

### 2.1 核心设计原则

1. **统一用户标识层**：引入 `account_id`（全局唯一），在入口处将渠道身份映射为统一 ID
2. **渐进改造**：不重写现有代码，通过适配层（Adapter）接入
3. **渠道感知**：保持对话 / 记忆的渠道隔离（同一用户在不同渠道有独立对话上下文）
4. **并发安全**：SQLite WAL 模式 + 简单悲观锁

### 2.2 新架构概览

```
                    ┌─────────────────────────────────────┐
                    │          User Identity Layer         │
                    │         (user_identity.py)           │
                    │                                      │
                    │  feishu_open_id ──→ account_id       │
                    │  weixin_user_id ──→ account_id       │
                    │                                      │
                    │  account_id → [feishu, weixin, ...]  │
                    └────────────────┬────────────────────┘
                                     │
        ┌────────────────────────────┼────────────────────────────┐
        │                            │                            │
        ▼                            ▼                            ▼
┌──────────────────┐    ┌─────────────────────┐    ┌──────────────────────┐
│  Feishu Adapter  │    │  WeChat Adapter      │    │  Channel-agnostic    │
│ (feishu_adapter) │    │ (weixin_adapter)     │    │  Handler             │
│                  │    │                      │    │  (统一走              │
│  1. 提取 open_id │    │  1. 提取 FromUserName│    │   LearningAgent)     │
│  2. 映射→account │    │  2. 映射→account    │    │                      │
│  3. 调用 Agent   │    │  3. 调用 Agent      │    │  对话管理 ✓          │
│                  │    │                      │    │  意图分类 ✓          │
│                  │    │                      │    │  Quiz ✓              │
└──────────────────┘    └─────────────────────┘    └──────────────────────┘
                                     │
                                     ▼
                    ┌─────────────────────────────────────┐
                    │         Memory Layer                 │
                    │                                      │
                    │  所有表：user_id → account_id        │
                    │  新增：account_id + channel 联合主键 │
                    └─────────────────────────────────────┘
```

### 2.3 新增模块

#### 2.3.1 `user_identity.py` — 统一用户标识层

**核心数据结构**（新增表）：

```sql
-- 账号-渠道映射表
CREATE TABLE IF NOT EXISTS user_accounts (
    account_id   TEXT PRIMARY KEY,           -- 全局唯一用户 ID（UUID 或 hash）
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL
);

-- 渠道身份映射表
CREATE TABLE IF NOT EXISTS channel_identities (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id   TEXT NOT NULL,               -- 关联全局账号
    channel      TEXT NOT NULL,               -- 'feishu' / 'weixin' / 'weixin_group'
    channel_uid  TEXT NOT NULL,               -- 渠道原始 ID（open_id / FromUserName）
    created_at   TEXT NOT NULL,
    UNIQUE(channel, channel_uid),             -- 一个渠道身份只能映射一个账号
    FOREIGN KEY (account_id) REFERENCES user_accounts(account_id)
);

CREATE INDEX IF NOT EXISTS idx_channel_identity 
    ON channel_identities(channel, channel_uid);
```

**核心函数**：

```python
def resolve_user(channel: str, channel_uid: str) -> str:
    """
    根据渠道 + 渠道用户 ID 解析为全局 account_id。
    
    逻辑：
    1. 查 channel_identities 是否有映射
    2. 有 → 返回 account_id
    3. 无 → 新建 account_id（UUID），建立映射，返回
    """
    pass

def link_identities(account_id: str, channel: str, channel_uid: str) -> None:
    """
    将渠道身份关联到已有账号（手动绑定）。
    用于用户希望跨渠道统一身份的场景。
    """
    pass

def get_all_channels(account_id: str) -> List[Dict[str, str]]:
    """获取一个账号关联的所有渠道身份"""
    pass
```

**为什么不用既有 `user_profiles.user_id`？**  
`user_profiles` 当前已存储数据，直接改主键为 `account_id` 需要迁移且影响 `/users/register` API。新增独立的 `user_accounts` + `channel_identities` 表更安全，通过适配层在入口处完成映射。

#### 2.3.2 `feishu_adapter.py` — 飞书适配层

**目标**：将飞书消息路由到 `LearningAgent.process_message`，与企微一致。

```python
def handle_feishu_message_adapted(open_id: str, user_text: str, dedup_key: str) -> str:
    """
    取代 handle_feishu_message 中的 LLM 直接回复逻辑，
    改走 LearningAgent。
    
    Steps:
    1. account_id = resolve_user('feishu', open_id)
    2. reply = LearningAgent.process_message(account_id, 'feishu', user_text)
    3. 返回 reply
    """
    pass
```

**变更范围**：
- `handle_feishu_message` 中 "fallback chat" 分支 → 调用 `handle_feishu_message_adapted`
- 保留 onboarding / search / RAG 分支（这些不是通用消息处理）

#### 2.3.3 `weixin_adapter.py` — 企微适配层（最小变更）

企微已在走 `LearningAgent.process_message`，只需要在入口处添加 `resolve_user`：

```python
# 在 weixin_callback_handle 中：
# actual_user → account_id = resolve_user('weixin', actual_user)
# agent.process_message(account_id, 'wechat', content_text)
```

### 2.4 DB Schema 改造

#### 2.4.1 现有表改造策略

| 表名 | 当前 user_id 含义 | 改造方案 |
|------|------------------|---------|
| `user_profiles` | 企微 user_id / 任意 | 新增 `account_id` 列（可空），逐步迁移 |
| `learning_progress` | 企微 user_id | 新增 `account_id` 列 |
| `reading_history` | user_id | 新增 `account_id` 列 |
| `digest_history` | user_id | 新增 `account_id` 列 |
| `dialogue_sessions` | user_id + channel | `user_id` 改为 `account_id` |
| `dialogue_turns` | 通过 session 关联 | 无需改 |
| `greetings_history` | open_id | 新增 `account_id` 列 |
| `user_conversations` | user_id | 新增 `account_id` 列 |

**改造顺序**（可分多步实施）：

```
Step 1: 新建 user_accounts + channel_identities 表
Step 2: dialogue_sessions.user_id → account_id（不影响现有对话）
Step 3: 新增 `account_id` 列到所有业务表
Step 4: 后台脚本填充 account_id（从 channel_identities 反向填充）
Step 5: 改 `user_profiles.user_id` 为全局 account_id（可选，可保留兼容）
```

#### 2.4.2 dialogue_sessions 改造

```sql
-- 当前：user_id + channel 唯一
-- 改造：account_id + channel 唯一
ALTER TABLE dialogue_sessions 
ADD COLUMN account_id TEXT DEFAULT '';
```

改造后 `DialogueManager.get_or_create_session`：

```python
def get_or_create_session(self, account_id: str, channel: str) -> int:
    # 同时兼容新旧数据：先按 account_id 查，再按 user_id 查
    row = conn.execute(
        "SELECT id FROM dialogue_sessions WHERE account_id=? AND channel=?",
        (account_id, channel)
    ).fetchone()
```

### 2.5 关键代码变更清单

#### 2.5.1 `dapper_coding_agent.py`

| 位置 | 变更 |
|------|------|
| `handle_feishu_message` fallback 聊天分支 | 改为 `handle_feishu_message_adapted`，走 `LearningAgent` |
| `weixin_callback_handle` | 入口添加 `resolve_user('weixin', actual_user)` |
| `_handle_weixin_feedback` | `user_id` → `resolve_user('weixin', user_id)` |
| `save_to_memory(open_id, ...)` | 改为 `save_to_memory(account_id, ...)` |
| `get_recent_memory(open_id, ...)` | 改为 `get_recent_memory(account_id, ...)` |

#### 2.5.2 `memory.py`

| 位置 | 变更 |
|------|------|
| `get_profile(user_id)` | 兼容旧 `user_id` 和新 `account_id` |
| `get_all_active_users()` | 返回 `account_id` |
| `register_user(user_id, ...)` | 同时创建 `user_accounts` 和 `channel_identities` |

#### 2.5.3 `dialogue_manager.py`

| 位置 | 变更 |
|------|------|
| `get_or_create_session(user_id, channel)` | `user_id` → `account_id`，兼容旧数据 |
| `cleanup_old_sessions(hours)` | 加定时调度 |

#### 2.5.4 `learning_agent.py`

| 位置 | 变更 |
|------|------|
| `process_message(user_id, ...)` | 接口不变，但传入的已是 `account_id` |
| `_reflect(user_id, ...)` | 更新时使用 `account_id` 写入 memory |

---

## 3. 多用户数据隔离策略

### 3.1 存储层隔离

所有业务表按 `account_id` 过滤：

```python
# 当前（无隔离保证）：
conn.execute("SELECT * FROM user_profiles")

# 改造后（强制 account_id 过滤）：
def get_profile(account_id):
    conn.execute("SELECT * FROM user_profiles WHERE account_id = ?", (account_id,))
```

**硬约束**：上层业务代码**只能通过 `memory.py` 的函数**访问数据，不直接操作 SQL。这些函数统一接收 `account_id` 参数。

### 3.2 对话隔离

对话已通过 `dialogue_sessions(user_id, channel)` 按用户隔离。改造后改为 `(account_id, channel)`，确保：
- 不同渠道的用户对话完全隔离
- 同一用户在不同渠道有其独立的对话上下文
- 对话上下文不超过 `limit=10` 轮次

### 3.3 定时任务隔离

`run_digest_job` 已按 `user_id` 循环分发：

```python
users = get_all_active_users()  # 改造后返回 account_id 列表
for user_id in users:
    run_tech_digest(user_id=user_id, ...)
```

✅ 当前已天然隔离，只需将 `user_id` 换为 `account_id`。

---

## 4. 多用户并发处理

### 4.1 当前风险

Python 的 FastAPI + `uvicorn.run` 默认多线程：
- `feishu_webhook` 使用 `background_tasks.add_task` → 后台线程处理
- `weixin_callback` 直接在请求处理函数中执行
- SQLite 默认在**序列化模式**（serialized），并发写可能导致 `database is locked` 错误

### 4.2 并发方案

#### 4.2.1 SQLite 配置优化（立即生效）

```python
# 所有数据库连接开启 WAL 模式
with sqlite3.connect(DB_PATH) as conn:
    conn.execute("PRAGMA journal_mode=WAL")  # 写不阻塞读
    conn.execute("PRAGMA busy_timeout=5000")  # 等待 5 秒再报错
```

在 `init_memory_db()` 中添加这些 PRAGMA。

#### 4.2.2 简单悲观锁（操作级别）

对于写操作密集的场景（如 `update_profile`、`save_to_memory`），使用文件锁：

```python
import fcntl  # 仅限 Linux
# 或使用 Portalocker（跨平台）

def _with_lock(func):
    """用文件锁保护关键写操作"""
    def wrapper(*args, **kwargs):
        lock_file = DB_PATH + ".lock"
        with open(lock_file, 'a') as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                return func(*args, **kwargs)
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
    return wrapper
```

Windows 备选：使用 `msvcrt.locking` 或简单使用 `threading.Lock`（因为线程模型已知）。

#### 4.2.3 内建 threading.Lock（推荐方案）

由于当前服务是单进程多线程模型，最优方案是 `threading.Lock`：

```python
# memory.py 中添加全局锁
import threading
_memory_lock = threading.Lock()

def get_profile(user_id):
    with _memory_lock:
        # 原有逻辑
        ...
```

**适用性**：
- `get_profile`、`update_profile`、`record_reading`、`record_digest` 等关键写函数加锁
- 读操作（纯 SELECT）不加锁
- `init_memory_db` 加锁（避免并发初始化冲突）

### 4.3 Webhook 请求队列（远期方案）

如果需要**严格的请求顺序保证**（如飞书事件的有序性），引入内存队列：

```python
from queue import Queue
from threading import Thread

_feishu_queue: Queue[Dict] = Queue()

def feishu_worker():
    while True:
        event = _feishu_queue.get()
        try:
            handle_feishu_message_adapted(event)
        finally:
            _feishu_queue.task_done()

# 启动 worker thread
_worker = Thread(target=feishu_worker, daemon=True)
_worker.start()

@app.post("/feishu/webhook")
async def feishu_webhook(request, background_tasks):
    body = await request.body()
    _feishu_queue.put(body)  # 入队，worker 串行处理
```

**当前无需做**，先做 WAL + 锁方案。队列方案仅在并发写冲突频繁时引入。

---

## 5. 实施步骤

### Phase 17.1: 用户身份映射层（必需，优先级最高）

```
清单：
□ 创建 user_identity.py
  □ init_identity_db() - 创建 user_accounts + channel_identities 表
  □ resolve_user(channel, channel_uid) -> account_id
  □ link_identities(account_id, channel, channel_uid)
  □ get_all_channels(account_id)
□ 分别在 feishu 和 weixin 入口调用 resolve_user
□ 在现有 memory.py 函数中兼容 account_id 和旧 user_id
□ 基础测试：飞书用户 → account_id → memory 存储 → 正确隔离
```

### Phase 17.2: 飞书消息走 LearningAgent（高优先级）

```
清单：
□ 创建 feishu_adapter.py
  □ handle_feishu_message_adapted(open_id, user_text) -> reply
□ 改造 handle_feishu_message fallback 分支
  □ 保留 onboarding / search / RAG 分支不动
  □ fallback → feishu_adapter → LearningAgent
□ 此时飞书用户也有了对话管理、意图分类、quiz 检测
```

### Phase 17.3: 并发安全（中优先级）

```
清单：
□ 所有 conn.execute 前加 PRAGMA (WAL + busy_timeout)
□ memory.py 关键写函数加 _memory_lock
□ init_memory_db + lock
```

### Phase 17.4: 数据迁移（低优先级，可分批）

```
清单：
□ dialogue_sessions 新增 account_id 列
□ user_profiles 新增 account_id 列（可空）
□ 后台脚本：遍历已有 user_id，反向同步 account_id
□ 飞书 greetings_history 的表，open_id 同步到 channel_identities
□ /users/list API 返回 account_id
```

---

## 6. 风险与回退

| 风险 | 概率 | 影响 | 应对 |
|------|------|------|------|
| `resolve_user` 新表建失败 | 低 | 所有新用户无法处理 | try-except 降级为直接用 channel_uid 作为 user_id |
| 飞书改走 LearningAgent 后回复风格变化 | 中 | 用户体验不一致 | 在 LearningAgent 中检测 `channel='feishu'` 调整回复风格 |
| SQLite WAL + 锁引入死锁 | 低 | 服务卡死 | 锁加 timeout，超时降级为不加锁处理 |
| 已有数据的 `user_id` 和 `account_id` 冲突 | 低 | 数据混乱 | 全部用 UUID 做 account_id，绝不重复 |
| 飞书 onboarding 分流和 LearningAgent 冲突 | 中 | 新用户 onboarding 不生效 | 保留 onboarding 分支优先级高于 LearningAgent |

---

## 7. 回退方案

每个子 Phase 完成后**必须 git commit**：

```bash
git commit -m "✅ Phase 17.1: 用户身份映射层
- 新增 user_identity.py
- 飞书/企微入口 resolve_user
- memory.py 兼容新旧标识"
```

发现严重问题可：

```bash
git revert HEAD  # 回退到上一个已提交的稳定版本
```

---

## 8. 测试清单

| 测试项 | 通过条件 |
|--------|---------|
| 飞书用户发消息 | 回复正常，dialogue_sessions 中有记录 |
| 企微用户发消息 | 回复正常，identity mapping 正确 |
| 飞书 + 企微同真实用户 | 两个渠道映射到不同 account_id（默认不绑定） |
| 两个用户同时发消息 | 各自隔离，互不干扰 |
| 飞书用户 onboarding | 仍然正常工作 |
| 企微用户 quiz 检测 | LearningAgent 正确处理 |
| API 接口兼容 | `/users/list`, `/users/register` 正常工作 |
| 定时 Digest 任务 | 正确按 account_id 分发 |
