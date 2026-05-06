# Learning Scout v2 - 项目文档

> 最后更新：2026-04-29

---

## 项目概述

**Learning Scout** 是一个基于企业微信的教育智能体，主打"每日课程推送 + 智能问答"。

核心能力：
- 每日 08:05 自动推送个性化 AI 学习课程
- 用户可追问课程内容（基于上下文的对话式教学）
- 自适应难度调整（根据反馈自动升降难度）
- Tech Digest 每日 AI 资讯简报

**技术栈：** Python 3.12 / FastAPI / SQLite / 企业微信 API / Tavily Search / LLM

---

## 项目结构

```
/opt/Dapper_Coding_Agent/
├── dapper_coding_agent.py      # 主服务入口（FastAPI），处理企微回调 + 路由
├── learning_scout.py            # 学习陪伴核心逻辑（课程生成/推送/学情跟踪）
├── lesson_generator.py          # LLM 生成结构化课程
├── learning_agent.py            # 智能体主循环（意图分类/规划/工具执行）
├── tech_digest.py               # Tech Digest 资讯采集与推送
├── weixin_client.py            # 企业微信应用客户端
├── weixin_callback.py           # 企业微信回调解密（URL 验证版）
├── dialogue_manager.py          # 对话历史管理
├── planner.py                   # 意图分类与规划
├── tool_executor.py             # 工具执行器
├── memory.py                    # 用户记忆层
├── dapper_memory.db             # SQLite 数据库
├── requirements.txt
└── venv/                       # Python 虚拟环境
```

---

## 核心数据模型

### learning_events（学情事件）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| user_id | TEXT | 用户标识 |
| event_type | TEXT | lesson_sent / positive_feedback / negative_feedback |
| created_at | TEXT | 时间戳 |

### learning_progress（学习进度）
| 字段 | 类型 | 说明 |
|------|------|------|
| user_id | TEXT | 用户标识 |
| direction | TEXT | 学习方向（主键） |
| total_days | INTEGER | 总天数 |
| current_day | INTEGER | 当前进度 |
| difficulty_level | TEXT | beginner / intermediate / advanced |
| lessons_sent | INTEGER | 已推送课程数 |

### generated_lessons（已生成课程）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| user_id | TEXT | 用户标识 |
| direction | TEXT | 学习方向 |
| day | INTEGER | 第几天 |
| title | TEXT | 课程标题 |
| content_md | TEXT | 完整 Markdown 内容 |
| level | TEXT | 难度级别 |
| created_at | TEXT | 时间戳 |

### learning_plans（学习计划）
| 字段 | 类型 | 说明 |
|------|------|------|
| user_id | TEXT | 用户标识 |
| direction | TEXT | 学习方向 |
| day | INTEGER | 第几天 |
| title | TEXT | 课程标题 |
| content_summary | TEXT | 内容摘要 |

---

## 消息处理流程

```
企业微信消息
    ↓
weixin_callback_handle (dapper_coding_agent.py)
    ↓
检查是否为反馈消息（👍/👎）？
    ├─ Yes → _handle_weixin_feedback()
    │         ├─ record_learning_event(user_id, type)
    │         ├─ adjust_difficulty_level(user_id, direction)
    │         └─ 回复确认消息
    │
    └─ No → LearningAgent.process_message()
              ├─ _is_learning_query() ← 标题关键词匹配
              │   ├─ 相关 → teach_with_context()
              │   └─ 不相关 → _fallback_teach()
              │             ├─ 尝试 Tavily 搜索（15s超时）
              │             └─ 有/无结果 → LLM 回答
              └─ planner.plan() → tool_executor.execute()
```

---

## 自适应难度规则

| 条件 | 动作 |
|------|------|
| 连续 3 次正面反馈 | beginner → intermediate → advanced |
| 连续 5 次无反馈 | 降一级 |
| 任何负面反馈 | 立即降一级 |

---

## 定时任务

| 时间 | 任务 | 函数 |
|------|------|------|
| 08:05 | 每日课程推送 | push_daily_lesson() |
| 08:10 | Tech Digest 推送 | run_digest_job() |

---

## 已知的网络限制

阿里云国内服务器访问海外 API：
- Tavily（api.tavily.com）：无代理直连会被墙，已设 15s 超时降级
- Tavily SDK 会自动读取 HTTPS_PROXY / HTTP_PROXY 环境变量
- 如有海外代理，在 .env 中配置 HTTPS_PROXY=http://代理:端口

---

## Git

```bash
cd /opt/Dapper_Coding_Agent
git tag -l          # 查看标签
git log --oneline   # 查看提交历史
```

当前 tag：v2.0-phases9-13（2026-04-29）
