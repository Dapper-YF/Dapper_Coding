# PROJECT_MEMORY.md - Learning Scout v2 核心定位

> 最后更新：2026-05-05（补录5月进展）

---

## 核心定位

**Learning Scout = 学习助手 + 教学智能体**

不是单纯的信息推送机器人，而是：
- **学习者**：能抓取、吸收、理解新知识
- **教学者**：能把知识消化后，用用户能懂的方式教给用户

---

## 两大核心能力

### 1. 学习能力（信息消化）

| 能力 | 状态 | 说明 |
|------|------|------|
| 多源采集 | ✅ | Tavily 搜索 + RSS + 网页抓取 |
| 内容理解 | ✅ | LLM 摘要 + 知识点提取 |
| 知识存储 | ✅ | RAG 向量知识库（embosit-m2.7B） |
| 结构化 | ✅ | 提取关键概念、术语、关系 |

### 2. 教学能力（知识输出）

| 能力 | 状态 | 说明 |
|------|------|------|
| 因材施教 | ✅ | 根据 mastery_score 调整深度（Phase 15） |
| 多形式输出 | ✅ | 文字讲解 + 练习题 + 总结 |
| 交互式学习 | ✅ | 用户可以提问、追问、做题 |
| 学习路径 | ✅ | 自适应路径（Phase 15） |
| 知识检测 | ✅ | 课后测验（Phase 14） |

---

## 智能体成长机制

### 当前有（被动成长）

- 用户点击/忽略 → 调整推送权重
- 难度反馈 → 调整内容深度
- 答题结果 → mastery_score 更新 → 推送模式调整

### Phase 15 自适应规则（2026-04-30）

| mastery 范围 | 推送模式 | 说明 |
|-------------|---------|------|
| ≥ 0.8 + 连续 3 天 | fast | 精简版课程 + 综合题 |
| 0.6 ~ 0.8 | normal | 正常完整课程 |
| 0.4 ~ 0.6 | reinforce | 同主题强化（多举例）|
| < 0.4 | review | 复习推荐，跳过新课 |

**薄弱阈值**：0.4（Architect × Supervisor 共识）

---

## 当前进度

| 组件 | 状态 | 说明 |
|------|------|------|
| 每日推送 | ✅ 完成 | 08:05 课程 + 08:10 Tech Digest |
| 课后测验 | ✅ 完成 | Phase 14（2026-04-30）|
| 自适应路径 | ✅ 完成 | Phase 15（2026-04-30）|
| 语义理解 | ⚠️ 待升级 | 当前用关键词，需改 LLM 判断 |
| 飞书交互 | ⚠️ 部分 | 对话能力已有，需要增强 |
| RAG 知识库 | ✅ 完成 | embosit-m2.7B 向量搜索 |

---

## 下一步开发计划

1. **Phase 16**：语义理解升级 — `_is_learning_query` 改用 LLM 判断
2. **多用户支持**：用户主动发消息自动注册学习路径
3. **Tavily 代理配置**：.env 配置 HTTPS_PROXY（国内服务器访问海外）
4. **飞书对话增强**：接入更多事件类型

---

## 2026-04-30 补充：企微图片处理 + SSH 密钥修复

### 企微图片处理（P0）
- 文件：`dapper_coding_agent.py`（`weixin_callback_handle`）
- 逻辑：图片消息（msg_type='image'）→ 通过企业微信媒体接口下载（media_id）→ PIL + pytesseract OCR → LearningAgent 智能回复
- 服务已重启生效（PID 1097322）
- 注意：服务器未安装 pytesseractOCR依赖（pillow已装），待测

### SSH 上传通道修复
- 原因：之前用错误的密钥 `id_rsa_openclaw`，服务器实际使用密码认证
- 解决方案：将 `C:\Users\Dapper\.ssh\id_rsa_openclaw.pub` 公钥加入服务器 `/root/.ssh/authorized_keys`
- 结果：现在可直接用密钥 SSH/SCP，不再卡死

---

## 2026-04-30 评估 + P0 修复

### 评估概述
- 测试集：33题，覆盖8个维度
- Baseline：纯 LLM（MiniMax M2.7，无搜索）
- Learning Scout：有搜索（Bing）+ RAG + LLM
- 评估框架：5维度（accuracy/depth/clarity/usefulness/overall），1-5分制

### 总体结论
- **LS 均分 3.69 vs Baseline 均分 3.75**（差距 0.06）
- LS 整体接近 Baseline，但深度和实用价值系统性偏弱

### 各维度表现
| 维度 | LS胜率 | 结论 |
|------|--------|------|
| 事实准确性 | ~3% | ✅ 相当 |
| 深度与完整度 | 6% | ⚠️ LS系统性偏弱 |
| 表达清晰度 | ~3% | ✅ LS略优 |
| 实用价值 | 6% | ⚠️ LS缺可操作建议 |
| 综合评分 | 6% | ⚠️ LS整体偏弱 |

### P0 问题（5道技术类题目 LS 败）
Q1 光合作用 / Q5 RESTful API / Q6 Python list-tuple / Q7 快速排序 / Q9 Git rebase-merge

### 根因
1. Bing 搜索质量差（搜到不相关内容）
2. max_tokens=600 限制（回答被截断）
3. _fallback_teach Prompt 缺少深度要求

### P0 修复进行中（2026-04-30 修复）
- subagent fix-p0-search：搜索质量检查 + 二次优化
- subagent fix-p0-prompt：max_tokens→1500 + 深度Prompt

### lesson_generator.py 已修复（2026-04-30）
- `_call_llm` 新增 `max_tokens` 参数支持

---

## 智能体训练流程（Agent Training Workflow）

> 适用场景：Learning Scout 回答质量不达预期时，通过系统化提问→评估→修复→复测来提升智能体能力
> 经验值：每轮训练可提升均分 0.1~0.3，最终目标超越 Baseline 或差距 < 0.1

### 整体流程

```
┌─────────────────────────────────────────────────────────────┐
│  ① 准备测试集                                               │
│    - 收集用户高频问题 / 薄弱知识点                           │
│    - 整理成「测试题集」（含标准问题和期望答案）               │
│    - 评估题应覆盖多个难度/类型维度                          │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│  ② 初始评估（Baseline vs 当前版本）                          │
│    - 用测试集同时跑 Baseline（纯LLM）和 Learning Scout       │
│    - 多维度打分（事实准确性/深度/清晰度/实用价值/综合）       │
│    - 输出：逐题对比表 + 各维度均分 + P0/P1 问题列表          │
│    - 工具：eval_report.xlsx（4 Sheet：逐题/汇总/P0/P1）     │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│  ③ 根因分析                                                │
│    - 汇总 P0 问题（LS 明显败的题目）                         │
│    - Supervisor + Architect 共同分析：                       │
│      · 搜索问题？→ 搜索质量/关键词/重试逻辑                 │
│      · 回答深度问题？→ max_tokens / Prompt 深度指令         │
│      · 表达问题？→ Prompt 表达要求                          │
│      · 知识盲区？→ RAG 知识库 / 搜索结果                    │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│  ④ P0 修复（优先级最高）                                     │
│    - 并行 spawn subagent：                                   │
│      · fix-p0-search：搜索关键词清洗 + 质量检查 + 二次重试   │
│      · fix-p0-prompt：max_tokens + 深度 Prompt              │
│    - 修复后上传服务器 + 重启服务（supervisorctl restart）    │
│    - 验证：语法检查 + 文件内容确认                           │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│  ⑤ P1 修复（进一步提升）                                     │
│    - 根据 P0 修复后仍未改善的题目决定修复方向                 │
│    - 常见 P1 修复方向：                                      │
│      · 搜索扩展：num_results 5→8，timeout 10→15            │
│      · 关键词扩展：_extract_core_terms 取更多词              │
│      · Prompt 深度：11条规则（技术/分析/实用分类专项指令）   │
│      · max_tokens 进一步调整                                 │
│    - 修复后上传服务器 + 重启                                  │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│  ⑥ 企微 Bot 复测                                           │
│    - 用企微 Bot 手动发消息测试 P0/P1 题目                    │
│    - 观察：回答长度 / 深度 / 实用性 / 搜索结果                │
│    - 记录仍有问题的题目 → 进入下一轮 P2 修复                  │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│  ⑦ 效果评估 + 存档                                          │
│    - 对比：修复前均分 vs 修复后均分                          │
│    - Git commit：阶段性成果 + 评估结论                       │
│    - 更新 PROJECT_MEMORY.md（修复记录 + 结论）               │
└─────────────────────────────────────────────────────────────┘
```

### 当前进度（2026-05-05 更新）

| 轮次 | 状态 | 评估均分 | 说明 |
|------|------|---------|------|
| 第1轮 | ✅ 完成 | LS 3.69 vs BL 3.75 | 初始评估，发现5道P0 + 深度不足 |
| 第2轮 | ✅ 修复已部署 | 待复测 | P0+P1修复已部署（搜索+深度Prompt+扩展）|
| 第2轮复测 | ⏳ **待执行** | - | 企微 Bot 手动测试 Q1/Q5/Q6/Q7/Q9 |
| 第3轮 | 🔲 待定 | - | 根据复测结果决定是否需要 P2 |

### 关键文件位置

| 文件 | 路径 | 用途 |
|------|------|------|
| 评估报告 | `E:\Study\Dapper_Coding\eval_report.xlsx` | 4 Sheet 评估结果 |
| 测试题集 | `E:\Study\Dapper_Coding\_run_eval.py` | 33题测试集 |
| Learning Scout | `/opt/Dapper_Coding_Agent/learning_agent.py` | 核心文件（服务器） |
| 本地副本 | `E:\Study\Dapper_Coding\learning_agent.py` | 核心文件（本地，版本可能落后） |
| 服务进程 | `supervisorctl restart dapper-coding-agent` | 重启命令 |
| 服务器SSH | `root@8.162.10.45` | 上传文件 + 重启 |

### 常用修复代码位置

| 问题类型 | 代码位置 | 修复参数 |
|---------|---------|---------|
| 搜索质量 | `learning_agent.py` `_fallback_teach` | 清洗 + 重试逻辑 |
| 回答深度 | `learning_agent.py` `system_prompt` | max_tokens（当前1500）|
| 深度Prompt | `learning_agent.py` `system_prompt` | 11条规则 |
| 搜索扩展 | `learning_agent.py` `_bing_search` | num_results（当前8）/ timeout（当前15）|
| 关键词扩展 | `learning_agent.py` `_extract_core_terms` | terms[:5] / len≤4 |

### 训练原则

1. **每轮只修1-2类问题**：不要同时改太多，无法定位有效修复
2. **先 P0 后 P1**：P0 问题影响最大，优先解决
3. **复测是必须的**：代码改了不验证等于没改
4. **记录对比**：每轮评估存档，对比均分变化
5. **根因比修复更重要**：找到真正原因才能根治

---

## 🚨 P0 Bug 状态（截至4月30日）

**问题**：`max_tokens` 参数传递错误，`_call_llm()` 不接受此参数 → 所有 Level 2 LLM 调用降级 → 回答仅21字 fallback

**建议行动**：
1. 检查服务器 `/opt/Dapper_Coding_Agent/learning_agent.py` 的 `_call_llm` 方法签名
2. 确认 `lesson_generator.py` 修复是否已同步到服务器
3. 在企微 Bot 上手动测试 Q1，看服务器端是否正常

---

## 2026年5月重大进展

### 5月1日：Step 5 BottomNav 完成

| Step | 内容 | 状态 |
|------|------|------|
| Step 1 | Domain Model + Room | ✅ |
| Step 2 | DI + Retrofit | ✅ |
| Step 3 | ChatScreen + ViewModel | ✅ |
| Step 4 | KnowledgeGraphScreen | ✅ |
| Step 5 | BottomNav 整合 | ✅ |
| Step 5.1 | VPS 部署 api_routes.py + nginx | 🔲 待做 |

### 5月2日：CC CLI 限制发现 + onboarding 后端上线

**CC CLI 根本限制（重要）**：
- `--allowedTools` 让 CC 能调用 Bash，但创建新文件时仍触发权限确认
- `--dangerously-skip-permissions` 对 Write 操作无效
- CC 在非交互模式下遇到 Write 操作会输出描述而非真正创建文件
- 简单任务（改现有文件、执行脚本）✅，多文件创建 ❌

**确立工作流**：
| 任务类型 | 执行方 | 我的角色 |
|---------|--------|---------|
| 复杂/多文件/关键代码 | 用户 → CC CLI | 写提示词 + 验证 |
| 小任务/单文件 | subagent / exec | 派发 + 验证 |
| 分析/调研 | subagent / 我直接做 | 直接处理 |
| 部署/VPS | exec + SSH | 直接执行 |

**onboarding 后端已上线**：
- POST /api/auth/register ✅
- POST /api/auth/login ✅
- GET /api/onboarding/tree ✅
- POST /api/onboarding/complete ✅

### 5月3日：CC 全面审计 APP + 战略重置

**CC 审计结果**（21项问题）：
- P0 × 5 全部修复 ✅
- P1 × 9 全部修复 ✅
- P2 × 1 修复 ✅
- 未修复 7 项（需后端 API 配合）

**战略优先级重大调整**：
- **旧**：Agent 优先，APP 是附庸
- **新**：APP 是融资门面，Agent 是后台能力
- **原因**：认知状态机需要长期使用才能感知，甲方第一眼只看 APP 外观
- **差异化目标**：知识图谱 + Markdown + 文件生成（Word/Excel/PDF）+ 对话历史 + 图谱联动

**APK 发布**：`http://8.162.10.45/app-debug.apk`（17MB，含 CC 审计修复）

### 5月4日：项目记忆重写

- 重写 `dapper-coding-agent\PROJECT_MEMORY.md`（战略级更新）
- 确立 Phase 18+ APP 优先战略
- 列出 P0/P1/P2 待修复清单

### 5月5日凌晨：飞书 API 超时诊断

- Gateway 正常运行 ✅
- `open.feishu.cn` 无法访问（国内网络问题，可能是 VPN/防火墙/代理）
- Control UI 正常（WebSocket 长连接没问题）
- 建议：`Test-NetConnection open.feishu.cn -Port 443` 检查网络

---

## Subagent 执行日志（5月）

| 时间 | Agent | 任务 | 结论 |
|------|-------|------|------|
| 2026-05-03 | CC | 全面修缮APP（14项修复） | ✅ 编译通过 |
| 2026-05-03 | CC | 实现APP内版本更新 | ✅ |
| 2026-05-03 | subagent brainstorm | 认知状态机头脑风暴 | 7个成长维度 |
| 2026-05-04 | Architect | 重写项目记忆（战略重述）| APP 优先，Agent 暂停 |

---

## Phase 进度追踪（完整）

| Phase | 状态 | 关键结论 |
|-------|------|---------|
| Phase 0-13 | ✅ 完成 | 每日推送 + 对话式教学基础 |
| Phase 14 | ✅ 完成 | 知识掌握检测（quiz_engine + mastery_score） |
| Phase 15 | ✅ 完成 | 自适应学习路径（4模式推送：fast/normal/reinforce/review） |
| Phase 16 | ✅ 完成 | onboarding后端：注册/登录/JWT/问卷/人设API |
| Phase 17 | ✅ 完成 | APP UI修缮（CC审计 14 项修复）|
| **Phase 18+** | 🔲 **APP优先**，Agent待深入 | 认知状态机暂停，专注 APP 体验完善 |

---

## 已部署 API（VPS）

| 端点 | 状态 | 备注 |
|------|------|------|
| POST /api/auth/register | ✅ | |
| POST /api/auth/login | ✅ | |
| GET /api/auth/verify | ✅ | |
| GET /api/onboarding/tree | ✅ | |
| POST /api/onboarding/complete | ✅ | |
| GET /api/user/profile | ✅ | 需补充真实用户名 |
| GET /api/user/onboarding-status | ✅ | |
| GET /api/app/version | ✅ | |
| POST /api/chat | ✅ | 需补充 timestamp + title + insight_chips |
| GET /api/discover | 🔲 待开发 | APP Discover 页假数据 |
| GET /api/conversations | 🔲 待开发 | 多 Session 管理 |

---

## 新增 API 待开发

| API | 优先级 | 说明 |
|-----|--------|------|
| GET /api/discover | P1 | 返回用户未掌握 topics |
| GET /api/conversations | P0 | 对话 Session 列表含 title |
| POST /api/chat → 响应加 timestamp | P0 | 消息级时间戳 |
| POST /api/chat → 响应加 insight_chips | P1 | 上下文推荐问题 |
| POST /api/chat → 响应加 title | P1 | 首条消息生成标题 |
| GET /api/graph/generate | P0 | 根据用户问卷定制图谱 |
| GET /api/user/profile → 真实用户名 | P0 | 注册时填写的名字 |
| POST /api/user/avatar | P2 | 头像上传 |
| GET /api/user/stats | P0 | 真实学习天数、概念数、活跃度 |

---

## 2026年5月待完成 P0 任务

| 任务 | 优先级 | 状态 |
|------|--------|------|
| 企微 Bot P0 题目复测 | P0 | ⏳ 待执行 |
| Chat Agent 不回复排查（N1）| P0 | 🔲 待排查 |
| 对话历史存储（Room）| P0 | 🔲 待实现 |
| 多 Session 管理 | P0 | 🔲 待实现 |
| 用户真实用户名 API | P0 | 🔲 待实现 |
| 定制化图谱生成 API | P0 | 🔲 待实现 |

---

## 协作规范（已确立）

| 规范 | 说明 |
|------|------|
| 复杂代码任务 | 用户执行 CC CLI，Architect 写提示词+验证 |
| 小任务 | subagent / exec |
| CC 提示词 | 必须包含三步反思：意图挖掘→上帝视角→更优解 |
| 设计稿缺失 | 立即说，不要跳 |
| CC 有审计权 | CC 发现问题可直接修复 |
| **禁止** | 用 subagent 假装 CC |

---

## 文档路径

| 文档 | 路径 |
|------|------|
| 全局 CLAUDE.md | C:\Users\Dapper\.claude\CLAUDE.md |
| 后端 CLAUDE.md | E:\Study\Dapper_Coding\CLAUDE.md |
| 后端项目记忆 | E:\Study\Dapper_Coding\.project_memory\PROJECT_MEMORY.md |
| APP 项目记忆 | C:\Users\Dapper\.openclaw\projects\Dapper_Coding_App\PROJECT_MEMORY.md |
| CC 提示词参考 | E:\temp\CC_COMMAND_PROTOCOL.md |
| CC 决策记录 | E:\temp\CC_DECISION_LOG.md |

---

*「Learning Scout 不仅要告诉你世界发生了什么，还要能教你搞懂它。」*

*本文件随每次对话更新。最后更新：2026-05-05*
