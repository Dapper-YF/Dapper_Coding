# 企业微信主动推送 - 设计文档

> **调研时间**：2026-05-01  
> **代码路径**：E:\Study\Dapper_Coding  
> **目标**：设计统一的 `POST /weixin/push` 接口，支持企业微信应用主动向用户推送消息

---

## 1. 现有推送能力分析

### 1.1 推送通道一览

| 通道 | 技术实现 | 代码位置 | 消息格式 | 可触达范围 |
|------|----------|----------|----------|------------|
| **应用消息** | WeiXinClient (`/cgi-bin/message/send`) | `weixin_client.py` | text / markdown / news / textcard | 指定用户 (`touser`) |
| **群聊消息** | WeiXinClient (`/cgi-bin/chat/send`) | `weixin_client.py` | text / markdown | 指定群聊 (`chatid`) |
| **Webhook 群机器人** | HTTP POST (`/cgi-bin/webhook/send`) | `tech_digest.py` | text / markdown / image / news | 群内所有成员 |

### 1.2 已有推送实现

#### A. Tech Digest 简报推送（`tech_digest.py`）

```
push_to_weixin(content)          ← Webhook 群机器人，纯文本
send_digest_card(title, content) ← 应用消息 Markdown，降级到 Webhook
```

- **逻辑**：优先用 `WeiXinClient.send_markdown()`，失败降级到 `push_to_weixin()` (Webhook)
- **问题**：`push_to_weixin()` 只支持 `msgtype: text`，不支持富文本
- **用户粒度**：批量遍历 `get_all_active_users()`，逐个推送

#### B. 每日课程推送（`learning_scout`）

- `push_daily_lesson` 由 APScheduler 每天 08:05 触发
- 依赖 `learning_scout` 模块（本地无此文件，部署在 VPS `/opt/Dapper_Coding_Agent/`）
- 推送渠道：企业微信应用消息

#### C. 用户回复（`dapper_coding_agent.py`）

- 收到消息 → LearningAgent 处理 → WeiXinClient 回复
- `send_text()` 或 `send_text_to_chat()`

### 1.3 现有推送的问题

| 问题 | 影响 |
|------|------|
| **两条通道并存，无统一接口** | 新功能（如 quiz 提醒）不知该用哪条通道 |
| **Webhook 只支持 text** | 简报降级后格式差，用户体验下降 |
| **无推送频率控制** | 多个定时任务可能短时间内连续推送 |
| **无推送记录** | 无法追溯"谁收到了什么" |
| **quiz 待答无主动提醒** | 用户有未答题，但系统不会主动通知 |

---

## 2. 企业微信 API 能力（调研）

### 2.1 应用消息推送

| API | 用途 | 限制 |
|-----|------|------|
| `POST /cgi-bin/message/send` | 向指定用户发消息 | 需 `touser`（UserID），受"可信 IP"限制 |
| `POST /cgi-bin/message/batch/send` | 批量发送（最多 1000 人） | 同上 |
| `POST /cgi-bin/message/update` | 更新已发消息（Card 类型） | 仅支持 textcard/news 类型 |

**消息类型**：

| msgtype | 特点 | 适用场景 |
|---------|------|----------|
| `text` | 纯文本，支持 `\n` 换行 | 简单通知 |
| `markdown` | 企业微信 Markdown（有限语法） | 简报、格式化内容 |
| `news` | 图文卡片（标题+描述+链接+图） | 文章推荐 |
| `textcard` | 文本卡片（标题+描述+按钮） | 交互式通知 |

### 2.2 群聊消息推送

| API | 用途 |
|-----|------|
| `POST /cgi-bin/chat/send` | 向指定群聊发消息 |
| `POST /cgi-bin/externalcontact/message/send` | 向外部联系人发消息 |

### 2.3 Webhook 群机器人

| API | 格式 | 限制 |
|-----|------|------|
| `POST /cgi-bin/webhook/send` | text / markdown / image / news / file / voice / template_card | 每分钟最多 20 条，群内所有人可见 |

---

## 3. 统一推送接口设计

### 3.1 接口定义

```
POST /weixin/push
```

**请求体**：

```json
{
  "channel": "app",
  "target": "user123",
  "msg_type": "markdown",
  "content": "## 今日课程\n\n你有一道待答题...",
  "title": "待答提醒",
  "url": "https://example.com/quiz/123",
  "priority": "normal",
  "source": "quiz_engine",
  "idempotency_key": "quiz_remind_user123_20260501"
}
```

**字段说明**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `channel` | string | ✅ | 推送通道：`app`（应用消息）/ `webhook`（群机器人）/ `chat`（群聊） |
| `target` | string | ✅ | 目标：UserID / chatid / webhook URL（channel=webhook 时可为空） |
| `msg_type` | string | ✅ | 消息类型：`text` / `markdown` / `news` / `textcard` |
| `content` | string | ✅ | 消息正文 |
| `title` | string | ❌ | 标题（textcard/news 必填） |
| `url` | string | ❌ | 链接（textcard/news 必填） |
| `picurl` | string | ❌ | 图片 URL（news 类型） |
| `priority` | string | ❌ | 优先级：`urgent` / `normal`（默认）/ `low` |
| `source` | string | ❌ | 来源标识，用于日志和去重 |
| `idempotency_key` | string | ❌ | 幂等键，防重复推送（24h 内相同 key 不重复发送） |

**响应**：

```json
{
  "ok": true,
  "message_id": "msg_xxx",
  "channel": "app",
  "sent_at": "2026-05-01T16:30:00+08:00"
}
```

### 3.2 推送策略

```
收到 POST /weixin/push
    │
    ├── 1. 幂等检查（idempotency_key）
    │      └── 24h 内重复 → 返回 { ok: true, deduped: true }
    │
    ├── 2. 通道选择
    │      ├── channel=app   → WeiXinClient._send_message()
    │      ├── channel=chat  → WeiXinClient._send_chat_message()
    │      └── channel=webhook → push_to_weixin()
    │
    ├── 3. 格式适配
    │      ├── text     → 直接发送
    │      ├── markdown → 企业微信 Markdown（注意：不支持标准 Markdown 全语法）
    │      ├── news     → 构造 WeiXinArticle 列表
    │      └── textcard → 构造 textcard payload
    │
    ├── 4. 降级策略
    │      ├── app 发送失败 → 尝试 webhook（如有配置）
    │      └── webhook 失败 → 记录失败日志
    │
    └── 5. 记录推送日志
           └── push_logs 表（id, user_id, channel, source, status, created_at）
```

---

## 4. 现有代码复用分析

### 4.1 可直接复用

| 组件 | 位置 | 复用方式 |
|------|------|----------|
| `WeiXinClient._send_message()` | `weixin_client.py:68` | 通道=app 的核心发送 |
| `WeiXinClient._send_chat_message()` | `weixin_client.py:98` | 通道=chat 的核心发送 |
| `WeiXinClient.send_text/markdown/news/textcard()` | `weixin_client.py:115-148` | 消息格式适配 |
| `get_weixin_client()` | `weixin_client.py:151` | 客户端初始化 |
| `push_to_weixin()` | `tech_digest.py:321` | 通道=webhook 的发送 |

### 4.2 需要封装

| 组件 | 说明 |
|------|------|
| **幂等性检查** | 新增 `push_logs` 表，24h 内相同 `idempotency_key` 不重复发送 |
| **推送频率限制** | 同一用户 1 分钟内最多 3 条，同一 source 1 小时内最多 5 条 |
| **推送日志** | 记录每次推送的 channel/target/source/status |
| **降级逻辑** | app → webhook 降级链 |

### 4.3 新增组件

```python
# push_engine.py（建议新增文件）

class PushEngine:
    """统一推送引擎"""
    
    def __init__(self):
        self.weixin_client = get_weixin_client()
        self.webhook_url = os.getenv("WEIXIN_WEBHOOK_URL", "")
        self._init_push_db()
    
    def push(self, channel, target, msg_type, content, **kwargs) -> dict:
        """统一推送入口"""
        # 1. 幂等检查
        if kwargs.get("idempotency_key") and self._is_duplicate(kwargs["idempotency_key"]):
            return {"ok": True, "deduped": True}
        
        # 2. 频率检查
        if not self._check_rate_limit(target):
            return {"ok": False, "error": "rate_limited"}
        
        # 3. 执行推送
        result = self._do_push(channel, target, msg_type, content, **kwargs)
        
        # 4. 记录日志
        self._log_push(target, channel, kwargs.get("source", ""), result)
        
        return result
    
    def _do_push(self, channel, target, msg_type, content, **kwargs):
        if channel == "app":
            return self._push_app(target, msg_type, content, **kwargs)
        elif channel == "chat":
            return self._push_chat(target, msg_type, content, **kwargs)
        elif channel == "webhook":
            return self._push_webhook(content, **kwargs)
        return {"ok": False, "error": "unknown channel"}
```

---

## 5. 场景适配设计

### 5.1 场景 1：每日课程推送（现有）

| 属性 | 值 |
|------|-----|
| 触发 | APScheduler cron 08:05 |
| channel | `app` |
| target | 每个活跃用户的 UserID |
| msg_type | `markdown` |
| source | `daily_lesson` |
| 优先级 | `normal` |

**复用**：`push_daily_lesson()` 内部调用 `PushEngine.push()`，替代直接调用 WeiXinClient。

### 5.2 场景 2：Tech Digest 简报推送（现有）

| 属性 | 值 |
|------|-----|
| 触发 | APScheduler cron 08:10 |
| channel | `app`（优先）→ `webhook`（降级） |
| target | 每个活跃用户的 UserID |
| msg_type | `markdown` |
| source | `tech_digest` |
| 优先级 | `normal` |

**复用**：`send_digest_card()` 和 `push_to_weixin()` 的逻辑统一到 `PushEngine`。

### 5.3 场景 3：Quiz 待答提醒（新增）

| 属性 | 值 |
|------|-----|
| 触发 | 用户完成课程后延迟 30 分钟，或定时扫描 |
| channel | `app` |
| target | 当前用户 UserID |
| msg_type | `textcard`（带"去答题"按钮） |
| source | `quiz_reminder` |
| 优先级 | `urgent` |
| 幂等键 | `quiz_remind_{user_id}_{lesson_id}` |

**新增逻辑**：

```python
# 在 quiz_engine.py 或新增 quiz_reminder.py 中

def check_and_remind_quiz(user_id: str):
    """检查用户是否有未答题，如有则推送提醒"""
    from quiz_engine import get_pending_quiz
    pending = get_pending_quiz(user_id)
    if not pending:
        return
    
    from push_engine import PushEngine
    engine = PushEngine()
    
    engine.push(
        channel="app",
        target=user_id,
        msg_type="textcard",
        content="你有一道课后测验待完成！",
        title="📝 测验待答提醒",
        url=f"https://your-domain.com/quiz/{pending['id']}",
        priority="urgent",
        source="quiz_reminder",
        idempotency_key=f"quiz_remind_{user_id}_{pending['lesson_id']}",
    )
```

---

## 6. 数据库变更

### 6.1 新增 `push_logs` 表

```sql
CREATE TABLE IF NOT EXISTS push_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    idempotency_key TEXT,
    user_id TEXT NOT NULL,
    channel TEXT NOT NULL,          -- app / chat / webhook
    source TEXT DEFAULT '',         -- quiz_reminder / daily_lesson / tech_digest
    msg_type TEXT NOT NULL,         -- text / markdown / textcard / news
    status TEXT NOT NULL,           -- success / failed / deduped / rate_limited
    error TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now', '+8 hours'))
);

CREATE INDEX IF NOT EXISTS idx_push_logs_user ON push_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_push_logs_idempotency ON push_logs(idempotency_key);
CREATE INDEX IF NOT EXISTS idx_push_logs_created ON push_logs(created_at);
```

### 6.2 幂等性查询

```python
def _is_duplicate(self, key: str) -> bool:
    """24h 内相同 key 视为重复"""
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT 1 FROM push_logs WHERE idempotency_key = ? AND created_at > datetime('now', '-1 day', '+8 hours')",
            (key,)
        ).fetchone()
        return row is not None
```

---

## 7. API 路由注册

在 `dapper_coding_agent.py` 中注册新路由：

```python
from push_engine import PushEngine

class PushRequest(BaseModel):
    channel: str           # app / chat / webhook
    target: str            # UserID / chatid
    msg_type: str          # text / markdown / news / textcard
    content: str
    title: Optional[str] = ""
    url: Optional[str] = ""
    picurl: Optional[str] = ""
    priority: Optional[str] = "normal"
    source: Optional[str] = ""
    idempotency_key: Optional[str] = ""

@app.post("/weixin/push", response_model=dict)
def weixin_push(body: PushRequest) -> dict:
    """统一推送接口"""
    engine = PushEngine()
    result = engine.push(
        channel=body.channel,
        target=body.target,
        msg_type=body.msg_type,
        content=body.content,
        title=body.title,
        url=body.url,
        picurl=body.picurl,
        priority=body.priority,
        source=body.source,
        idempotency_key=body.idempotency_key,
    )
    return result
```

---

## 8. 实施建议

### Phase 1：基础推送引擎

1. 新建 `push_engine.py` —— 统一推送入口
2. 新建 `push_logs` 表
3. 实现幂等性 + 频率限制
4. 注册 `POST /weixin/push` 路由

### Phase 2：迁移现有推送

5. `tech_digest.py` 的 `send_digest_card()` 改为调用 `PushEngine`
6. `learning_scout` 的 `push_daily_lesson()` 改为调用 `PushEngine`
7. 确认降级链（app → webhook）正常工作

### Phase 3：新增 Quiz 提醒

8. 新建 `quiz_reminder.py` —— 待答扫描 + 推送
9. 在课程完成时触发延迟提醒（30 分钟后检查）
10. 集成到 APScheduler（定时扫描兜底）

---

## 9. 风险与注意事项

| 风险 | 应对 |
|------|------|
| 企业微信应用消息**需要"可信 IP"白名单** | VPS IP 需在企微后台配置 |
| Webhook **每分钟最多 20 条** | 批量推送需加 sleep 间隔 |
| Markdown 语法受限（不支持标准 MD） | 只用 `**加粗**`、`[链接](url)`、`# 标题` |
| `touser` 字段需要用 **UserID** 而非 OpenID | 需确认现有 user_id 格式是否匹配 |
| Quiz 提醒可能打扰用户 | 只在用户活跃时段（8:00-22:00）推送 |

---

## 10. 总结

**核心设计**：统一的 `PushEngine` 封装企业微信三条推送通道（应用消息 / 群聊 / Webhook），提供幂等性、频率控制、推送日志。

**三个场景全部覆盖**：
- ✅ 每日课程推送 → 复用现有 `push_daily_lesson`，切换到 `PushEngine`
- ✅ Tech Digest 简报 → 复用现有 `send_digest_card`，切换到 `PushEngine`
- ✅ Quiz 待答提醒 → 新增 `quiz_reminder.py`，使用 `textcard` 类型推送

**最大复用**：`weixin_client.py` 的 `WeiXinClient` 100% 复用，只在其上层封装 `PushEngine`。
