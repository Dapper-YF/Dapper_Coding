# TASK_CURRENT.md - 企业微信 & 飞书对话智能体

## Context

- 项目路径：`E:\Study\Dapper_Coding`
- 云服务器：IP 8.162.10.45
- 企业微信：Corp ID `YOUR_WEIXIN_CORP_ID`，Agent ID `1000002`
- 飞书：已有配置

## Goal

实现企业微信和飞书的对话智能体，参考 OpenClaw 智能体架构，具备：
1. 三层记忆体系（短期/中期/长期）
2. 意图 → 规划 → 工具 → 反思 循环
3. 教学智能体能力（学习+教学）

## 智能体架构

```
┌─────────────────────────────────────────┐
│              用户输入                     │
└─────────────────┬───────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│           Intent Classifier              │
│    意图分类：问答/搜索/学习/闲聊/教学      │
└─────────────────┬───────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│           Planner (规划器)               │
│   根据意图规划：需要哪些工具？输出格式？    │
└─────────────────┬───────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│           Tool Executor (工具执行)        │
│   - Tavily 搜索                         │
│   - RAG 知识库查询                      │
│   - LLM 生成                           │
│   - memory 查询                         │
└─────────────────┬───────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│           Reflector (反思器)             │
│   结果评估：是否需要补充？更新记忆？       │
└─────────────────┬───────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│           Memory Manager                 │
│   短期：当前会话（10轮/用户）             │
│   中期：用户画像、学习进度               │
│   长期：RAG 知识库                      │
└─────────────────────────────────────────┘
```

## 三层记忆设计

### 1. 短期记忆（Session）

```sql
CREATE TABLE dialogue_sessions (
    id INTEGER PRIMARY KEY,
    user_id TEXT NOT NULL,
    channel TEXT NOT NULL, -- 'wechat' / 'feishu'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE dialogue_turns (
    id INTEGER PRIMARY KEY,
    session_id INTEGER,
    role TEXT NOT NULL, -- 'user' / 'assistant'
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES dialogue_sessions(id)
);
-- 保留最近 10 轮，自动清理超时会话
```

### 2. 中期记忆（User Profile）

```sql
-- 扩展现有 user_profiles 表
ALTER TABLE user_profiles ADD COLUMN learning_level TEXT DEFAULT 'intermediate';
ALTER TABLE user_profiles ADD COLUMN interests TEXT DEFAULT '[]';
ALTER TABLE user_profiles ADD COLUMN learning_history TEXT DEFAULT '[]';
```

### 3. 长期记忆（Knowledge Base）

- 使用现有 RAG 模块（已有 `embosit-m2.7B`）
- 用户学习过的内容向量存入知识库
- 支持相似度检索

## 实现步骤

### Phase 1：基础设施

- [ ] 创建 `dialogue_manager.py`（短期记忆）
- [ ] 扩展 `memory.py`（中期记忆接口）
- [ ] 扩展 `knowledge_base.py`（长期记忆接口）

### Phase 2：智能体核心

- [ ] `intent_classifier.py`（意图分类）
- [ ] `planner.py`（规划器）
- [ ] `tool_executor.py`（工具执行）
- [ ] `reflector.py`（反思器）

### Phase 3：通道集成

- [ ] 企业微信对话（修复 POST 回调 + 回复）
- [ ] 飞书对话（增强事件处理）
- [ ] 统一回复格式

### Phase 4：教学智能体

- [ ] 学习路径生成
- [ ] 练习题生成
- [ ] 学习进度跟踪

## 约束

- 不破坏现有 08:10 推送功能
- 回复延迟 < 10 秒
- 云服务器资源有限
- LLM 调用成本可控

## 预期产出

- `dialogue_manager.py` - 对话管理
- `agent_core/` - 智能体核心模块
- 修改现有模块集成智能体

## 创建时间

2026-04-26
