# TASK_A7.md - Phase A7 企业微信深度集成

## Context

- 项目路径：`E:\Study\Dapper_Coding`
- 依赖文件：
  - `memory.py` - 用户管理
  - `tech_digest.py` - Digest 核心
  - `dapper_coding_agent.py` - API 服务
  - `weixin_client.py` - 企业微信客户端（新建）

## Goal

实现企业微信应用的深度集成，支持：
1. **Card 消息** - 更丰富的消息卡片格式
2. **Click-through 追踪** - 用户点击消息后跟踪反馈

## 企业微信配置

| 配置项 | 值 |
|--------|-----|
| Corp ID | YOUR_WEIXIN_CORP_ID |
| Agent ID | 1000002 |
| Corp Secret | `env:WEIXIN_CORP_SECRET` |

## Constraints

1. **兼容性**：保留现有 Webhook 推送作为降级方案
2. **安全性**：Access Token 自动刷新，不暴露
3. **错误处理**：推送失败时记录日志，不阻断主流程

## Steps

### Step 1：实现企业微信 API 客户端 ✅

- [x] 获取 Access Token（自动刷新）
- [x] 发送应用消息接口
- [x] 支持 Markdown 和 News 消息类型

### Step 2：实现 Card 消息推送 ✅

- [x] 创建 `WeiXinClient` 类
- [x] 实现 `send_text()` 方法
- [x] 实现 `send_markdown()` 方法
- [x] 实现 `send_news()` 方法（Card 格式）
- [x] 实现 `send_textcard()` 方法

### Step 3：集成到 Tech Digest ✅

- [x] 修改 `tech_digest.py` 的推送逻辑
- [x] 用户有企业微信配置时使用应用推送
- [x] 否则降级到 Webhook

### Step 4：实现 Click 回调处理 ✅

- [x] 添加 `/weixin/callback` POST 路由（处理点击事件）
- [x] 添加 `/weixin/callback` GET 路由（URL 验证）
- [x] 记录点击反馈并更新偏好

## 验收标准

- [x] 企业微信应用推送（Markdown 格式）
- [x] Card 消息格式（Markdown 支持）
- [x] 点击回调处理
- [x] 降级方案（Webhook）

## 新增文件

| 文件 | 说明 |
|------|------|
| `weixin_client.py` | 企业微信应用客户端（6KB）|

## 修改文件

| 文件 | 修改内容 |
|------|----------|
| `tech_digest.py` | 集成企业微信应用推送 |
| `dapper_coding_agent.py` | 添加回调处理接口 |
| `.env` | 添加企业微信配置 |

## 状态

**Phase A7 完成** ✅
