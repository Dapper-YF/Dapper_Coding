# Learning Scout v2 - 开发进度

> 最后更新：2026-04-30

---

## 2026-04-30：Phase 14-15 完成

### 🔴 紧急修复
- `learning_scout.py` 第 2596 行重复 try 块语法错误 → 导致当天 08:05/08:10 推送失败
- 手动修复语法 + 重启服务，已恢复正常

---

### Phase 14：知识掌握检测 ✅
- 新增 `quiz_engine.py`（出题/评判/mastery_score 管理）
- 新增数据库表：`lesson_assessments`、`mastery_records`
- `push_daily_lesson()` 末尾：推送课程后自动出 1 道选择题
- `learning_agent.py`：`process_message()` 优先检测未答题（A/B/C/D 路由）
- 支持跳过（"跳过"/"下一题" → mastery -0.1）
- 评判结果：答对 +0.2 / 答错 -0.3 / 跳过 -0.1
- **验证点**：空表默认值=0.5（不 crash）、INSERT OR REPLACE 防并发

### Phase 15：自适应学习路径 ✅
- `quiz_engine.py` 新增函数：
  - `get_mastery_record(user_id, topic)` — 查 mastery 记录
  - `save_mastery_record(...)` — 防并发写入
  - `get_adaptive_mode(user_id, topic)` — 判断推送模式
  - `get_previous_topic(user_id)` — 复习推荐用
- `learning_scout.py`：`push_daily_lesson()` 推送前查 mastery 决定模式
- `lesson_generator.py`：新增 `adaptive_mode` 参数（fast/normal/reinforce）

**自适应规则：**
| mastery 范围 | 模式 | 动作 |
|-------------|------|------|
| ≥ 0.8 + 连续 3 天 | fast | 精简压缩版课程 + 综合题 |
| 0.6 ~ 0.8 | normal | 正常完整课程 |
| 0.4 ~ 0.6 | reinforce | 同主题强化（多举例多对比）|
| < 0.4 | review | 发复习推荐，跳过新课生成 |

**薄弱阈值**：0.4（Supervisor 与 Architect 共识）

---

## 2026-04-29：Phase 9-13 完成

### Phase 9：LessonGenerator + 每日课程推送
- 新增 lesson_generator.py（453行）
- generate_lesson(topic, level, background) — LLM 生成结构化课程
- format_lesson_markdown() — 格式化微信推送
- push_daily_lesson() — 每日 08:05 推送
- get_user_current_topic() — 读 learning_plans 获取当前 day + topic
- 修复：_call_llm timeout 60s → 120s

### Phase 10：学情跟踪 + 自适应难度
- 新增 learning_events 表 + 索引
- 新增 learning_progress.difficulty_level / lessons_sent 列
- record_learning_event() / get_consecutive_counts()
- adjust_difficulty_level() / get_difficulty_level()

### Phase 11：用户反馈入口
- weixin_callback.py：unpad(..., 32) → unpad(..., 16)（解密 BUG）
- dapper_coding_agent.py：新增 _handle_weixin_feedback()

### Phase 12+13：课程持久化 + 对话式教学
- 新增 generated_lessons 表
- save_generated_lesson() / get_latest_generated_lesson()
- _is_learning_query() — 标题关键词匹配
- teach_with_context() — 基于课程上下文教学
- _fallback_teach() — Tavily 搜索 + LLM 诚实回答

---

## 待办 / 后续计划

- [ ] Phase 16：语义理解升级 — `_is_learning_query` 改用 LLM 判断（替代关键词匹配）
- [ ] Phase 17：多用户支持 — 用户主动发消息自动注册学习路径
- [ ] Tavily 代理配置 — .env 配置 HTTPS_PROXY
- [ ] 飞书对话能力 — 增强飞书事件处理

---

## Bug 修复记录

| 日期 | BUG | 文件 |
|------|------|------|
| 04-30 | try 块重复缩进语法错误（推送失败） | learning_scout.py |
| 04-29 | decrypt unpad 块大小 32→16 | weixin_callback.py |
| 04-29 | @app.post 装饰器错位（422） | dapper_coding_agent.py |
| 04-29 | _is_learning_query regex \x{4e00} 无效 | learning_agent.py |
| 04-29 | push_daily_lesson day 硬编码 1 | learning_scout.py |
| 04-29 | teach_with_context 追问全部记 positive | learning_agent.py |
| 04-29 | alert_msg 多行 f-string 语法错误 | tech_digest.py |
| 04-29 | Tavily 无 timeout（国内服务器卡死） | tech_digest.py |

---

## Git 存档

| 日期 | 标签 | 内容 |
|------|------|------|
| 2026-04-26 | v2.0-phases9-13 | Phase 9-13 完成 |
| 2026-04-30 | v2.0-phases14-15 | Phase 14+15 完成（待 commit）|
