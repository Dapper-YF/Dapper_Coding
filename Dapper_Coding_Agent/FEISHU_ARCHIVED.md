# 飞书功能归档说明

**归档日期**：2026-05-01  
**归档原因**：专注企业微信开发，飞书功能不再维护  
**归档方式**：代码注释保留（非删除），便于未来恢复

---

## 归档范围

### 1. 配置变量（保留为空值，避免 NameError）

| 变量 | 原用途 | 当前状态 |
|------|--------|----------|
| `FEISHU_APP_ID` | 飞书应用 ID | 保留空字符串 |
| `FEISHU_APP_SECRET` | 飞书应用密钥 | 保留空字符串 |
| `FEISHU_VERIFICATION_TOKEN` | 飞书事件校验 token | 保留空字符串 |
| `FEISHU_VERIFY_ENABLED` | 是否启用事件校验 | `False` |
| `FEISHU_SIMULATE` | 模拟模式开关 | `False` |

### 2. 注释掉的函数

| 函数名 | 原用途 | 行号范围 |
|--------|--------|----------|
| `get_tenant_access_token()` | 获取飞书 tenant_access_token | ~581-611 |
| `send_feishu_message()` | 向飞书用户发送文本消息 | ~742-789 |
| `run_daily_job()` | 每日问候定时任务（依赖飞书 API） | ~787-832 |
| `verify_feishu_event_token()` | 校验飞书事件回调 token | ~1827-1857 |
| `build_feishu_challenge_response()` | 处理飞书 URL 验证 challenge | ~1858-1877 |
| `log_non_challenge_event()` | 记录普通飞书事件日志 | ~1878-1882 |
| `handle_feishu_message()` | 处理飞书消息事件（含 OCR、搜索、RAG） | ~1914-2218 |

### 3. 注释掉的路由

| 路由 | 方法 | 原用途 |
|------|------|--------|
| `/feishu/webhook` | POST | 飞书回调入口 |
| `/feishu/events` | GET | 查看飞书入站消息（JSON） |
| `/feishu/events/view` | GET | 飞书入站消息可视化面板 |

### 4. 其他修改

- **FastAPI 标题**：从 `"Dapper Coding Feishu Webhook"` 改为 `"Dapper Coding Agent"`
- **模块文档字符串**：移除飞书推送描述，添加归档说明
- **`__main__` 启动逻辑**：跳过 `run_daily_job()` 调用和飞书事件校验

---

## 保留不变的代码

以下企业微信相关代码**完全未修改**：

- ✅ 企业微信配置变量（`WEIXIN_CORP_ID`、`WEIXIN_AGENT_ID` 等）
- ✅ `weixin_verify_signature()` - 企业微信签名验证
- ✅ `weixin_decrypt()` - 企业微信消息解密
- ✅ `weixin_decrypt_echo()` - 企业微信回调解密
- ✅ `/weixin/callback` (GET/POST) - 企业微信回调路由
- ✅ `_handle_weixin_feedback()` - 用户反馈处理
- ✅ 所有 `/users/*`、`/learning/*`、`/digest/*` API 路由
- ✅ `run_digest_job()` - Tech Digest 每日简报
- ✅ `start_scheduler()` - 调度器（保留企微相关任务）
- ✅ LLM 模块（`generate_greeting`、`generate_chat_reply`）
- ✅ 数据库模块（`init_memory_db`、`get_recent_memory`、`save_to_memory`）

---

## 恢复指南

如需恢复飞书功能：

1. 取消注释配置变量（填写真实值）
2. 取消注释 `get_tenant_access_token()` 函数
3. 取消注释 `send_feishu_message()` 函数
4. 取消注释 `handle_feishu_message()` 函数
5. 取消注释飞书路由（`/feishu/webhook`、`/feishu/events`）
6. 恢复 `__main__` 中的 `run_daily_job()` 调用
7. 恢复 FastAPI 标题

**提示**：搜索 `FEISHU_ARCHIVED` 标记可快速定位所有归档位置。

---

## 归档标记

代码中使用以下标记定位归档位置：

```
# --- FEISHU_ARCHIVED_START: handle_feishu_message ---
... (300+ 行注释代码)
# --- FEISHU_ARCHIVED_END: handle_feishu_message ---
```

搜索 `FEISHU_ARCHIVED` 可找到所有归档代码块。
