# TASK_CURRENT.md — Learning Scout v3 (反馈/系列/资源)

## 基本信息

- 触发时间：2026-04-17 16:03
- 依赖：阶段一（资料入库）+ 阶段二（向量搜索）已交付
- 执行人：GitHub Copilot
- 模式：用户反馈闭环 + 系列内容检测 + 多模态资源

---

## Context

### 当前状态

| 指标 | 数值 |
|------|------|
| 资料总数 | 约 50 条（全有 embedding） |
| 数据库表 | `learning_scout_items`（含 embedding 列） |
| 核心文件 | `learning_scout.py`（约 35KB）、`dapper_coding_agent.py`（约 55KB） |
| 依赖 | `numpy>=1.26.0`、`pypdf>=4.0.0` 已安装 |

---

## Goal

在阶段二基础上新增智能推荐与多模态能力：

1. **反馈追踪**：用户点击搜索结果中的链接时，记录 `click_count`，后续搜索加权
2. **系列检测**：标题含"第 X 篇"、"Part X"、"教程 X"等内容自动归为系列
3. **PDF/视频支持**：新增 `learning_resources` 表，存 PDF/视频元数据 + 提取的文本
4. **源推荐**：分析现有 feed 的引用关系，推荐相似高质量源

---

## Constraints

1. **阶段一/二逻辑不变**：不修改 `fetch_feed()`、`search_by_embedding()` 等已有函数的签名和行为
2. **反馈表设计**：新增 `learning_feedback` 表，记录 `item_id`、`open_id`、`action`（click/ignore）、`created_at`
3. **系列检测规则**：标题正则匹配 `第 [一二三四五六七八九十\d]+[篇章节部]`、`Part\s*\d+`、`教程\s*\d+` 等模式
4. **PDF 提取**：使用 `pypdf` 或 `pdfplumber`，不引入重型依赖
5. **视频字幕**：优先 B 站（简化处理：仅记录 URL），YouTube 用 `youtube-transcript-api`（可选）
6. **资源表设计**：`learning_resources` 表含 `item_id`、`resource_type`（pdf/video）、`url`、`local_path`、`extracted_text`、`created_at`
7. **搜索加权**：搜索结果排序时，`final_score = base_score * (1 + click_count * 0.1)`
8. **环境变量**：
   - `FEEDBACK_ENABLED`：反馈追踪开关，默认 `true`
   - `SERIES_DETECTION_ENABLED`：系列检测开关，默认 `true`
   - `RESOURCE_DOWNLOAD_ENABLED`：资源下载开关，默认 `false`（需用户显式开启）

---

## Steps

### Step 1 — requirements.txt 追加依赖

```
pypdf>=4.0.0
```

### Step 2 — 数据库扩展（反馈表 + 资源表）

新增 `migrate_add_feedback_and_resources_tables()` 函数：
- `learning_feedback` 表
- `learning_resources` 表
- `learning_scout_items` 表新增 `click_count`、`series_id` 列

### Step 3 — 反馈追踪函数

- `record_feedback(item_id, open_id, action)` — 记录用户反馈
- `get_item_click_count(item_id)` — 获取累计点击次数

### Step 4 — 搜索结果加权

修改 `search_by_embedding()`，应用反馈加权：
```python
final_score = base_score * (1 + click_count * 0.1)
```

### Step 5 — 系列内容检测

- `detect_series_id(title)` — 从标题提取系列 ID
- `detect_and_link_series(items)` — 对一批资料进行系列检测并更新 `series_id`

### Step 6 — 系列查询 API

```python
@app.post("/learning/series")
def learning_series(body: SeriesListRequest) -> dict:
    # 返回某系列的全部资料，按发布时间升序
```

### Step 7 — PDF/视频资源下载与提取

- `download_and_extract_pdf(url, item_id)` — 下载 PDF 并提取文本
- `process_resources_for_items(items)` — 对一批资料检测并下载资源

### Step 8 — 飞书搜索结果（简化）

飞书文本消息无法直接追踪点击，阶段三暂不实现，留待后续迭代。

### Step 9 — 智能源推荐（简化版）

- `recommend_similar_feeds(existing_feeds, limit=5)` — 基于现有订阅源的标签，推荐相似主题的新源
- `GET /learning/feed-recommendations` — 返回推荐列表

### Step 10 — 环境变量

```env
FEEDBACK_ENABLED=true
SERIES_DETECTION_ENABLED=true
RESOURCE_DOWNLOAD_ENABLED=false
```

---

## 文件清单

| 文件路径 | 操作 | 说明 |
|---------|------|------|
| `requirements.txt` | 修改 | 追加 `pypdf>=4.0.0` |
| `learning_scout.py` | 修改 | 新增反馈/系列/资源函数 |
| `dapper_coding_agent.py` | 修改 | 新增 `/learning/series`、`/learning/feed-recommendations` 路由 |
| `.env` | 修改 | 追加 FEEDBACK/SERIES/RESOURCE 开关 |

---

## 验收标准

- [ ] `learning_feedback` 表创建成功
- [ ] `learning_resources` 表创建成功
- [ ] `learning_scout_items` 表新增 `click_count`、`series_id` 列
- [ ] 搜索结果按 `final_score = base_score * (1 + click_count * 0.1)` 加权排序
- [ ] 标题含"第 X 篇"、"Part X"等内容自动归入系列
- [ ] `POST /learning/series` 返回某系列的全部资料
- [ ] PDF 链接自动下载并提取文本（`RESOURCE_DOWNLOAD_ENABLED=true` 时）
- [ ] `GET /learning/feed-recommendations` 返回 5 条以内推荐源
- [ ] `FEEDBACK_ENABLED=false` 时跳过反馈记录
- [ ] `SERIES_DETECTION_ENABLED=false` 时跳过系列检测

---

> 阶段三完成，Learning Scout 具备用户反馈、系列检测、资源处理能力。
