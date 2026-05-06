# TASK_FIX.md — Phase 7 修复任务书
_生成时间：2026-04-18 13:26_
_原因：Supervisor 审查发现 Phase 7 核心实现完全缺失_

---

## 根因

Copilot 只在 dapper_coding_agent.py 中写了对 Phase 7 函数的 **调用和 import**，但 learning_scout.py 中 **完全没有实现这些函数**。

---

## 修复范围

**仅修改 learning_scout.py**，不碰其他文件。

---

## 必须实现的函数（按顺序）

### 1. ConversationState Enum（Step 2）

`python
class ConversationState(Enum):
    INIT = "INIT"
    EXPLORING = "EXPLORING"
    DIRECTION_CONFIRMING = "DIRECTION_CONFIRMING"
    PATH_CONFIRMED = "PATH_CONFIRMED"
    LEARNING = "LEARNING"
`

### 2. FEAR_KEYWORDS 列表（Step 4）

`python
FEAR_KEYWORDS = [
    "太难了", "看不懂", "好难", "学不会",
    "放弃", "听不懂", "太复杂", "懵了",
    "不学了", "太难了", "脑子转不过来"
]
`

### 3. INIT_REPLY 模板（Step 8）

`python
INIT_REPLY = """太好了！AI 现在可是最火的领域之一。

简单说，AI 就是让机器学会"思考"和"学习"——
比如你用的 ChatGPT、智能推荐、刷脸支付，背后都是 AI。

AI 是个大家族，主要有几个方向：

🧠 机器学习（ML）— 让机器从数据中学习规律
🗣️ 自然语言处理（NLP）— 让机器读懂人类语言
👁️ 计算机视觉（CV）— 让机器看懂图片和视频
🎮 强化学习（RL）— 让机器通过试错做决策

对哪个感兴趣？或者有什么使用场景？比如聊天、推荐、自动驾驶？
"""
`

### 4. PUSH_TIME_ASK 模板（Step 9）

`python
PUSH_TIME_ASK = """收到！我们来设置你的推送时间 📋

每天大概能学多久？
A. 碎片时间（30分钟以内）
B. 稳定学习（1小时左右）
C. 集中冲刺（2小时以上）

希望我什么时候给你推送？
A. 早上（9:00）
B. 下午（14:00）
C. 晚上（20:00）
"""
`

### 5. get_user_conversation(user_id: str) -> Dict

从 SQLite user_conversations 表读取用户状态，不存在则插入默认记录。

### 6. save_user_conversation(user_id: str, **kwargs) -> None

将用户状态持久化回 user_conversations 表（updated_at 自动更新）。

### 7. detect_intent(message: str, current_state: str) -> str（Step 3）

识别以下意图并返回字符串标签：

| 返回值 | 触发条件 |
|--------|---------|
| 
ew_user | 消息含"我想学AI"、"AI新手"、"开始学习"等新用户入场词 |
| direction_selected | 消息含"NLP"、"CV"、"ML"、"RL"、"自然语言"、"计算机视觉"、"机器学习"、"强化学习" |
| path_confirmed | 消息含"好"、"开始"、"行"、"可以"、"是的" |
| path_rejected | 消息含"换"、"其他"、"不太想"、"不是" |
| ear_hard | 消息含 FEAR_KEYWORDS 中任意关键词 |
| sk_question | 消息含"总结"、"介绍一下"、"什么是"、"为什么"、"怎么做"、"帮我"、"解释"、"讲讲" |
| 	ime_selected | 当前状态为 PATH_CONFIRMED 且消息含时间/时长选项（如"A"、"B"、"C"、"30分钟"、"1小时"等） |
| unknown | 以上都不匹配 |

### 8. handle_onboarding(user_id: str, message: str) -> str（Step 5）

主入口函数：
1. 调用 get_user_conversation(user_id) 获取当前状态
2. 调用 detect_intent(message, current_state) 识别意图
3. 分发到对应状态处理函数（畏难和问答意图优先拦截，不改变状态）
4. 调用 save_user_conversation() 持久化状态变化
5. 返回 Bot 回复文本

### 9. 状态处理函数（Step 6）

`python
def state_init(user_id: str, message: str) -> str:
    """INIT：用户首次入场，发送 INIT_REPLY，状态 -> EXPLORING"""

def state_exploring(user_id: str, message: str) -> str:
    """EXPLORING：分析用户输入，推荐 NLP 方向 + 学习大纲，状态 -> DIRECTION_CONFIRMING"""

def state_direction_confirming(user_id: str, message: str) -> str:
    """DIRECTION_CONFIRMING：展示该方向学习路径大纲，询问确认
    - path_confirmed -> PATH_CONFIRMED
    - path_rejected -> EXPLORING"""

def state_path_confirmed(user_id: str, message: str) -> str:
    """PATH_CONFIRMED：询问推送时间和学习时长，发送 PUSH_TIME_ASK
    - time_selected -> LEARNING"""

def state_learning(user_id: str, message: str) -> str:
    """LEARNING：进入每日推送模式，调用 rag_qa() 处理用户问答"""
`

### 10. handle_fear(user_id: str, message: str) -> str

畏难处理函数：
- 从当前状态提取关键词（如果是学 NLP 的用户，说"NLP 其实不难"）
- 温柔语气 + 解释不难 + 简化内容 + 小步行动建议
- **不改变用户当前状态**

---

## 注意事项

1. **不修改已有 API 签名**：阶段一至六的函数保持原样
2. **RAG 问答复用**：LEARNING 状态的问答直接调用 ag_qa()
3. **数据库表已存在**：user_conversations 表已在 dapper_coding_agent.py 中创建
4. **对话风格**：前期轻松友好，使用 emoji / 短句
5. **不要加入练习题或评测题**

---

## 验收标准（修复完成后自检）

- [ ] ConversationState Enum 存在且 5 个状态齐全
- [ ] FEAR_KEYWORDS 列表存在且 ≥ 10 个词
- [ ] INIT_REPLY 模板存在且包含 AI 全景介绍
- [ ] PUSH_TIME_ASK 模板存在且询问时间和时长
- [ ] get_user_conversation() 能正确读取/创建用户状态
- [ ] save_user_conversation() 能正确持久化状态
- [ ] detect_intent() 能识别全部 8 种意图
- [ ] handle_onboarding() 能正确分发到各状态函数
- [ ] 各状态函数逻辑符合 TASK_CURRENT.md 中的状态转移规则
- [ ] handle_fear() 不改变用户当前状态
- [ ] 对话风格：emoji / 短句 / 友好语气

---

> 修复完成后通知 Supervisor 复查。
