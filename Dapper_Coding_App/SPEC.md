# Learning Scout APP - 产品规格说明书

> 项目路径：E:\Study\Dapper_Coding_App
> 最后更新：2026-05-01
> 状态：规划中

---

## 1. 产品定位

**Learning Scout APP** 是一款面向个人的 AI 学习助手客户端，通过对话式交互帮助用户构建、管理和复习知识。

**核心差异于企微 Bot：**
- 可视化知识图谱（自由拖拽布局）
- 本地知识管理（不依赖聊天记录）
- 完整的对话历史 + 知识沉淀

**目标用户：** 编程学习者，需要系统性整理知识的人

---

## 2. 核心功能

### 2.1 对话界面（Chat）

| 功能 | 描述 |
|------|------|
| 自然语言对话 | 调 VPS `/api/chat` 接口，streaming 响应 |
| 对话历史 | 按主题分组，支持搜索 |
| 上下文继承 | 新对话可选择引用历史上下文 |
| 知识提取 | 对话结束后，agent 自动提取知识点存入知识图谱 |

### 2.2 知识图谱（Knowledge Graph）

| 功能 | 描述 |
|------|------|
| 可视化布局 | Force-directed graph（力导向图），节点自由拖拽 |
| 节点类型 | 概念（圆形）、主题（方形）、关系（连线） |
| 关系标注 | 连线上标注关系类型：依赖 / 对比 / 扩展 |
| 手动编辑 | 添加节点、删除节点、修改关系 |
| 自动生成 | Agent 对话后自动分析，生成新节点/关系 |
| 折叠/展开 | 长按节点显示子节点，可折叠 |

**节点数据结构：**
```kotlin
data class KnowledgeNode(
    val id: String,
    val label: String,           // "Python 异步编程"
    val type: NodeType,          // CONCEPT / TOPIC
    val position: Offset,        // 屏幕坐标 (x, y)
    val parentId: String?,       // 父节点（用于折叠）
    val masteryScore: Float?,    // 0.0~1.0，来源于 quiz_engine
    val createdAt: Long,
    val updatedAt: Long,
)

data class KnowledgeEdge(
    val id: String,
    val fromNodeId: String,
    val toNodeId: String,
    val relationType: RelationType,  // DEPENDS_ON / CONTRASTS / EXTENDS
    val label: String?              // 可选的关系描述
)
```

### 2.3 学习报告（Report）

| 功能 | 描述 |
|------|------|
| 周报 | 自动生成每周学习摘要 |
| 掌握度趋势 | 折线图展示 mastery_score 变化 |
| 薄弱点分析 | AI 分析错题，给出改进建议 |
| 导出 | 生成 DOCX 下载 |

### 2.4 错题本 & 复习卡（Review）

| 功能 | 描述 |
|------|------|
| 错题集 | 从 quiz_engine 同步答错题目 |
| SRS 复习 | 基于 SM-2 算法的间隔复习 |
| 复习提醒 | 本地通知推送 |

---

## 3. 技术架构

### 3.1 技术栈

| 层次 | 技术 |
|------|------|
| UI | Jetpack Compose + Material 3 |
| 架构 | MVVM + Clean Architecture |
| 本地存储 | Room Database |
| API 调用 | Retrofit + OkHttp |
| 依赖注入 | Hilt |
| 图表绘制 | Compose Canvas（自定义） |
| 状态管理 | StateFlow + ViewModel |

### 3.2 项目结构

```
Dapper_Coding_App/
├── app/
│   └── src/main/
│       ├── java/com/learningscout/app/
│       │   ├── MainActivity.kt
│       │   ├── LearningScoutApp.kt          # Application class
│       │   │
│       │   ├── ui/
│       │   │   ├── screens/
│       │   │   │   ├── chat/
│       │   │   │   │   ├── ChatScreen.kt
│       │   │   │   │   └── ChatViewModel.kt
│       │   │   │   ├── graph/
│       │   │   │   │   ├── KnowledgeGraphScreen.kt
│       │   │   │   │   └── KnowledgeGraphViewModel.kt
│       │   │   │   ├── report/
│       │   │   │   └── ReportScreen.kt
│       │   │   │   └── review/
│       │   │   │       └── ReviewScreen.kt
│       │   │   │
│       │   │   └── components/
│       │   │       ├── DraggableNode.kt     # 可拖拽节点
│       │   │       ├── KnowledgeEdge.kt     # 节点连线
│       │   │       └── ChatBubble.kt
│       │   │
│       │   ├── data/
│       │   │   ├── local/
│       │   │   │   ├── AppDatabase.kt       # Room Database
│       │   │   │   ├── KnowledgeNodeDao.kt
│       │   │   │   ├── KnowledgeEdgeDao.kt
│       │   │   │   └── ChatMessageDao.kt
│       │   │   └── remote/
│       │   │       ├── ApiService.kt
│       │   │       ├── ApiClient.kt
│       │   │       └── dto/
│       │   │           ├── ChatRequest.kt
│       │   │           └── GraphResponse.kt
│       │   │
│       │   ├── domain/
│       │   │   ├── model/
│       │   │   │   ├── KnowledgeNode.kt
│       │   │   │   ├── KnowledgeEdge.kt
│       │   │   │   ├── ChatMessage.kt
│       │   │   │   └── LearningReport.kt
│       │   │   └── repository/
│       │   │       ├── KnowledgeRepository.kt
│       │   │       ├── ChatRepository.kt
│       │   │       └── ReportRepository.kt
│       │   │
│       │   └── di/
│       │       ├── AppModule.kt
│       │       └── NetworkModule.kt
│       │
│       └── res/
│           ├── values/
│           └── drawable/
│
├── build.gradle.kts
├── settings.gradle.kts
└── gradle.properties
```

### 3.3 后端 API（新增）

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/chat` | POST | 对话，streaming 响应 |
| `/api/chat/history` | GET | 获取对话历史 |
| `/api/graph/generate` | POST | 从对话内容生成知识图谱节点 |
| `/api/report/weekly` | GET | 生成周报 |
| `/api/quiz/errors` | GET | 获取错题列表 |

### 3.4 本地数据库（Room）

```sql
-- 知识节点表
CREATE TABLE knowledge_nodes (
    id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    type TEXT NOT NULL,           -- CONCEPT / TOPIC
    pos_x REAL NOT NULL,
    pos_y REAL NOT NULL,
    parent_id TEXT,
    mastery_score REAL,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    FOREIGN KEY (parent_id) REFERENCES knowledge_nodes(id)
);

-- 知识关系表
CREATE TABLE knowledge_edges (
    id TEXT PRIMARY KEY,
    from_node_id TEXT NOT NULL,
    to_node_id TEXT NOT NULL,
    relation_type TEXT NOT NULL,   -- DEPENDS_ON / CONTRASTS / EXTENDS
    label TEXT,
    FOREIGN KEY (from_node_id) REFERENCES knowledge_nodes(id),
    FOREIGN KEY (to_node_id) REFERENCES knowledge_nodes(id)
);

-- 聊天记录表（本地备份）
CREATE TABLE chat_messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL,            -- user / assistant
    content TEXT NOT NULL,
    timestamp INTEGER NOT NULL
);
```

---

## 4. 知识图谱 UI 设计

### 4.1 力导向图实现

```
Canvas 绘制流程：
1. 初始化节点位置（随机或层级布局）
2. 物理模拟：
   - 节点间排斥力（库仑力）
   - 连线吸引力（弹簧力）
   - 阻尼衰减
3. 每帧更新位置，绘制节点和连线
4. 处理手势：
   - 单指拖拽 → 移动节点
   - 双指捏合 → 缩放画布
   - 双指拖拽 → 平移画布
```

### 4.2 节点样式

| 状态 | 样式 |
|------|------|
| 默认 | 白色圆角矩形，阴影 |
| 选中 | 蓝色边框，发光效果 |
| 薄弱（mastery < 0.4）| 红色渐变边框 |
| 掌握（mastery > 0.8）| 绿色渐变边框 |

### 4.3 边样式

| 关系类型 | 颜色 |
|----------|------|
| 依赖（DEPENDS_ON）| 蓝色实线 |
| 对比（CONTRASTS）| 红色虚线 |
| 扩展（EXTENDS）| 绿色点线 |

---

## 5. MVP 优先级

| 阶段 | 功能 | 价值 |
|------|------|------|
| **MVP** | 对话界面 | 核心功能，能对话 |
| **MVP** | 知识图谱（可拖拽） | 差异化展示，能打动甲方 |
| **MVP** | 本地存储（Room） | 数据不丢失 |
| Phase 2 | 学习报告 | 扩展功能 |
| Phase 3 | 错题本 + SRS | 留存功能 |

---

## 6. 待确认

- [ ] API 认证方式（token？）
- [ ] 是否需要用户登录？
- [ ] 多端同步（APP + 企微数据互通？）
- [ ] 推送通知（本地还是服务端？）
