# TASK_CURRENT.md — Learning Scout v5 (RAG 问答)

## 基本信息

- 触发时间：2026-04-17 18:00
- 依赖：阶段一至四已交付
- 执行人：GitHub Copilot
- 模式：RAG（检索增强生成）问答

---

## Context

### 当前状态

| 指标 | 数值 |
|------|------|
| 资料总数 | 约 50 条（全有 embedding） |
| 搜索 API | `POST /learning/search`（语义搜索） |
| 飞书搜索 | 关键词识别"找/搜索/查一下" |
| LLM 配置 | MiniMax m2.7，`LLM_BASE_URL` / `LLM_API_KEY` 已配置 |

---

## Goal

实现**基于资料库的自然语言问答**：

1. **RAG 问答 API**：`POST /learning/ask`，输入问题，返回合成答案 + 引用列表
2. **飞书问答**：用户发"帮我总结一下 RAG 相关的资料"，识别为问答意图，返回格式化回答
3. **上下文组装**：Top-10 相关资料，每条含标题/摘要/链接
4. **回答质量**：500 字上限，仅基于提供的资料，不知道就说不知道
5. **引用格式**：文末列表，带可点击链接

---

## Constraints

1. **阶段一至四逻辑不变**：不修改已有函数的签名和行为
2. **Top-K 数量**：问答场景默认 10 条
3. **回答长度**：500 字上限，超出截断
4. **引用格式**：文末列表，格式 `[序号] 标题 - URL`
5. **无结果处理**：返回"未找到相关资料，建议换关键词试试"，不编造
6. **防幻觉 Prompt**：明确要求"仅使用提供的资料，不知道就说不知道"
7. **意图识别关键词**：`["总结", "介绍一下", "什么是", "怎么做", "为什么", "帮我", "解释"]`
8. **环境变量**：
   - `RAG_ENABLED`：RAG 问答开关，默认 `true`
   - `RAG_TOP_K`：检索资料数量，默认 `10`
   - `RAG_MAX_TOKENS`：回答最大字数，默认 `500`

---

## Steps

### Step 1 — 新增配置变量

```python
RAG_ENABLED = env_bool("RAG_ENABLED", True)
RAG_TOP_K = max(1, min(int(os.getenv("RAG_TOP_K", "10")), 20))
RAG_MAX_TOKENS = max(100, min(int(os.getenv("RAG_MAX_TOKENS", "500")), 2000))
```

### Step 2 — 上下文组装函数

```python
def build_rag_context(query: str, top_k: int) -> Tuple[str, List[Dict[str, Any]]]:
    # 检索相关资料并组装上下文
    # 返回：(context_text, items)
```

### Step 3 — RAG 回答生成函数

```python
def generate_rag_answer(question: str, context: str) -> str:
    # Prompt 约束：仅使用提供的资料，不知道就说不知道，500 字上限
```

### Step 4 — 引用格式化函数

```python
def format_rag_citations(items: List[Dict[str, Any]]) -> str:
    # 格式化引用列表：[序号] 标题 - URL
```

### Step 5 — 完整 RAG 问答函数

```python
def rag_qa(question: str) -> Tuple[str, str]:
    # 完整流程：检索 → 组装 → 生成 → 引用
```

### Step 6 — FastAPI 问答路由

```python
@app.post("/learning/ask")
def learning_ask(body: AskRequest) -> dict:
    # 返回 {answer, citations, total}
```

### Step 7 — 飞书问答意图识别

修改 `handle_feishu_message()`，新增 RAG 意图判断：
```python
RAG_KEYWORDS = ["总结", "介绍一下", "什么是", "怎么做", "为什么", "帮我", "解释", "讲讲"]
```

### Step 8 — 环境变量

```env
RAG_ENABLED=true
RAG_TOP_K=10
RAG_MAX_TOKENS=500
```

---

## 文件清单

| 文件路径 | 操作 | 说明 |
|---------|------|------|
| `learning_scout.py` | 修改 | 新增 RAG 相关函数 |
| `dapper_coding_agent.py` | 修改 | 新增 `/learning/ask` 路由 + 飞书问答路由 |
| `.env` | 修改 | 追加 RAG 配置 |

---

## 验收标准

- [ ] `POST /learning/ask` 返回结构化答案（answer/citations/total）
- [ ] 飞书发送"帮我总结一下 RAG 相关的资料"，收到 RAG 回答 + 引用列表
- [ ] 回答长度不超过 500 字
- [ ] 引用列表格式 `[序号] 标题 - URL`
- [ ] 无相关资料时返回"未找到相关资料，建议换关键词试试"
- [ ] LLM 不编造资料（Prompt 约束 + 温度 0.3）
- [ ] `RAG_ENABLED=false` 时跳过所有 RAG 逻辑
- [ ] 搜索意图（"找 XXX"）与 RAG 意图（"总结 XXX"）正确区分

---

> 阶段五完成，Learning Scout 具备基于资料库的智能问答能力。
