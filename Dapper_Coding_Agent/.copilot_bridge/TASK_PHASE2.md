# TASK_CURRENT.md — Learning Scout v2 (向量语义搜索)

## 基本信息

- 触发时间：2026-04-17 12:34
- 依赖：阶段一（learning_scout.py + feeds.yaml）已交付
- 执行人：GitHub Copilot
- 模式：向量语义搜索（Embedding + 余弦相似度）

---

## Context

### 核心文件

| 文件路径 | 说明 |
|---------|------|
| `learning_scout.py` | 阶段一核心逻辑，需扩展 |
| `dapper_coding_agent.py` | 已有 APScheduler + FastAPI 底座 |
| `dapper_memory.db` | SQLite，当前 schema 需扩展 |

### 当前数据库 Schema

```sql
CREATE TABLE learning_scout_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feed_name TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    published_at TEXT NOT NULL,
    summary TEXT NOT NULL,
    tags TEXT NOT NULL,
    content_hash TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    pushed INTEGER NOT NULL DEFAULT 0
);
```

---

## Goal

在阶段一基础上新增向量语义搜索能力：

1. **Embedding 入库**：对每条资料的 `summary` 生成向量，存入 SQLite BLOB
2. **语义检索 API**：`POST /learning/search`，自然语言 query，Top-K 返回最相关资料
3. **飞书对话搜索**：用户发"帮我找一下 RAG 相关资料"，Agent 调用搜索并返回结果
4. **增量索引**：新资料入库时自动生成 embedding，已有资料按批次后台回填

---

## Constraints

1. **阶段一逻辑不变**：不修改 `fetch_feed()`、`push_daily_learning()` 等已有函数的签名和行为
2. **向量存储方案**：纯 numpy + SQLite BLOB，不引入 Qdrant/Milvus 等外部向量库
3. **数据库扩展**：新增三列 `summary_embedding`（BLOB）、`embedding_model`（TEXT）、`embedding_at`（TEXT）
4. **Embedding 模型**：MiniMax Embedding API，调用 `POST {LLM_BASE_URL}/embeddings`
5. **相似度算法**：余弦相似度，纯 Python 手写，不引入 sklearn
6. **搜索上限**：单次最多返回 10 条，`top_k` 参数默认 5
7. **回填策略**：已有资料在 `run_learning_scout_job()` 执行时按批次处理，每批次 10 条
8. **API 路径**：`POST /learning/search`，请求体 `{"query": "string", "top_k": 5}`
9. **环境变量**：
   - `EMBEDDING_MODEL`：embedding 模型 ID，默认空字符串
   - `EMBEDDING_ENABLED`：开关，默认 `true`
10. **错误容忍**：embedding 生成失败不阻止资料入库，只记 WARNING 日志

---

## Steps

### Step 1 — requirements.txt 追加 numpy

```
numpy>=1.26.0
```

### Step 2 — 数据库 Migration

新增 `migrate_add_embedding_columns()` 函数，用 `ALTER TABLE ADD COLUMN` 检测并补充新列。

### Step 3 — Embedding 生成函数

```python
EMBEDDING_DIM = 1024

def generate_embedding(text: str) -> Optional[np.ndarray]:
    # 调用 MiniMax Embedding API
    # 维度校验，不符返回 None
```

### Step 4 — 向量存取与搜索函数

- `array_to_blob()` / `blob_to_array()` — numpy 与 BLOB 转换
- `save_embedding()` — 写入数据库
- `cosine_similarity()` — 手写余弦相似度
- `search_by_embedding()` — 语义搜索，返回 Top-K

### Step 5 — 增量索引

新增 `process_embeddings_for_items()`，在 `save_items()` 返回后独立处理 embedding 生成。

### Step 6 — 批量回填

新增 `backfill_missing_embeddings()`，每批次 10 条，批次间主动释放连接。

### Step 7 — FastAPI 搜索路由

```python
@app.post("/learning/search")
def learning_search(body: LearningSearchRequest) -> dict:
    from learning_scout import EMBEDDING_ENABLED, search_by_embedding
```

### Step 8 — 飞书对话搜索路由

修改 `handle_feishu_message()`，关键词识别：`["找", "搜索", "查一下", "有没有", "帮我找"]`

### Step 9 — 环境变量

```env
EMBEDDING_MODEL=embosit-m2.7B
EMBEDDING_ENABLED=true
```

---

## 文件清单

| 文件路径 | 操作 | 说明 |
|---------|------|------|
| `requirements.txt` | 修改 | 追加 `numpy>=1.26.0` |
| `learning_scout.py` | 修改 | 新增 embedding 相关函数 |
| `dapper_coding_agent.py` | 修改 | 新增 `/learning/search` 路由 + 飞书搜索路由 |
| `.env` | 修改 | 追加 EMBEDDING 配置 |

---

## 验收标准

- [ ] `learning_scout_items` 表新增 `summary_embedding`/`embedding_model`/`embedding_at` 三列
- [ ] `requirements.txt` 包含 `numpy>=1.26.0`
- [ ] 新资料入库后自动生成 embedding 并以 BLOB 形式存储
- [ ] `POST /learning/search` 返回 Top-K 相关资料（含 score）
- [ ] 飞书发送"帮我找一下 RAG 相关的资料"，收到搜索结果
- [ ] `run_learning_scout_job()` 执行时自动回填已有记录
- [ ] `EMBEDDING_ENABLED=false` 时跳过所有 embedding 逻辑
- [ ] embedding 生成失败时资料正常入库，仅记日志
- [ ] 余弦相似度手写实现，无 sklearn 依赖
- [ ] `generate_embedding()` 对维度异常的向量记录 WARNING 并返回 None

---

> 阶段二完成，Learning Scout 具备向量语义搜索能力。
