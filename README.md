<div align="center">

# 🧠 Learning Scout

### AI-Powered Personal Learning Ecosystem

**Full-stack intelligent learning platform — Android client + Python backend + enterprise messaging integration**

[![Kotlin](https://img.shields.io/badge/Kotlin-2.0-7F52FF?style=flat-square&logo=kotlin)](https://kotlinlang.org)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python)](https://python.org)
[![Jetpack Compose](https://img.shields.io/badge/Jetpack%20Compose-Material3-4285F4?style=flat-square)](https://developer.android.com/jetpack/compose)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](LICENSE)

---

</div>

## What is Learning Scout?

Learning Scout is a **full-stack AI learning assistant** that combines a native Android client with a Python backend to deliver personalized, AI-driven learning experiences. It's not a demo — it's designed for real users.

### Core Philosophy

> **From conversation to knowledge, from knowledge to mastery.**

Every AI conversation automatically extracts knowledge points, builds a visual knowledge graph, and feeds into a spaced repetition system — closing the loop between learning and retention.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Android Client (Kotlin)                    │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │ AI Chat  │  │  Learn   │  │  Graph   │  │  Profile   │  │
│  │ Streaming│  │  Daily   │  │  Force-  │  │  Settings  │  │
│  │ Sessions │  │  Courses │  │  Directed│  │  Dark Mode │  │
│  │ Export   │  │  Cards   │  │  Canvas  │  │  Update    │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬───────┘  │
│       │              │              │              │          │
├───────┴──────────────┴──────────────┴──────────────┴──────────┤
│                    Jetpack Compose + Hilt                     │
│                    Room DB + Retrofit + StateFlow             │
└──────────────────────────┬───────────────────────────────────┘
                           │ JWT Auth
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                  Python Backend (FastAPI)                     │
│                                                              │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────────┐  │
│  │  Chat API    │  │ Learning Scout│  │  Push Engine     │  │
│  │  /api/chat   │  │ RSS + LLM     │  │  Feishu/WeChat   │  │
│  │  Streaming   │  │ Summarize     │  │  Scheduled       │  │
│  └──────┬───────┘  └──────┬────────┘  └──────┬───────────┘  │
│         │                  │                   │              │
│  ┌──────┴──────────────────┴───────────────────┴──────────┐  │
│  │              MiniMax M2.7 LLM + SQLite                 │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

## Project Structure

```
Learning_Scout/
├── Dapper_Coding_App/          # 📱 Android Client (Kotlin)
│   ├── app/src/main/java/
│   │   └── com/learningscout/app/
│   │       ├── data/           # Room DB, Retrofit, Repository
│   │       ├── domain/         # Use Cases, Models
│   │       ├── ui/
│   │       │   ├── screens/    # Chat, Learn, Onboarding, Profile
│   │       │   ├── components/ # ChatBubble, UpdateDialog, etc.
│   │       │   ├── theme/      # Material 3 + Custom Gradients
│   │       │   └── navigation/ # Compose NavHost
│   │       └── di/             # Hilt Modules
│   └── SPEC.md                 # Product Specification
│
├── Dapper_Coding_Agent/        # 🐍 Python Backend
│   ├── dapper_coding_agent.py  # Main entry (Scheduler/Server)
│   ├── api_routes.py           # FastAPI routes
│   ├── learning_agent.py       # Learning Scout v3 engine
│   ├── push_engine.py          # Feishu/WeChat push
│   ├── memory.py               # SQLite memory layer
│   ├── admin/                  # Web admin dashboard
│   └── .env.example            # Environment template
│
└── README.md
```

## ✨ Android Client Features

### 💬 AI Chat with Streaming
- Real-time token-by-token response display
- Multi-session conversation management
- Export conversations to file
- Auto-scroll with smooth animations

### 📚 Daily Learning Content
- Personalized courses from Learning Scout
- AI-generated lesson cards with summaries
- Topic tagging and categorization
- Reading time estimates

### 🎓 Onboarding Survey
- 18-question tree-based user profiling
- Adaptive question flow based on answers
- Builds personalized learning preferences
- Stored locally via DataStore

### 🎨 Design System
- Material Design 3 with custom gradients
- Dark mode toggle
- Consistent color system (GradientStart → GradientEnd)
- Custom typography and shapes

### 🔄 Auto-Update
- Built-in version checker
- Changelog display
- Force update for critical releases
- Skip version option

### 🏗️ Technical Highlights
- **MVVM + Clean Architecture** — Clean separation of concerns
- **Hilt DI** — Compile-time dependency injection
- **Room DB** — Offline-first local storage
- **Retrofit + OkHttp** — Type-safe HTTP client
- **StateFlow** — Reactive state management
- **JWT Auto-refresh** — Transparent token renewal via interceptor

## 🐍 Backend Features

### Learning Scout v3
- RSS/Atom feed aggregation
- LLM-powered content summarization
- Smart tagging and categorization
- Feedback loop for content quality
- Series detection for related articles

### Push Engine
- Feishu OpenAPI integration
- WeChat Work webhook
- Scheduled daily briefings (08:00)
- Multi-format card messages

### Web Admin Dashboard
- FastAPI + static file hosting
- HTTP Basic Auth protection
- Push log viewer
- Learning item browser

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Android UI** | Jetpack Compose + Material 3 |
| **Android Arch** | MVVM + Clean Architecture |
| **Android DI** | Hilt |
| **Android DB** | Room |
| **Android Net** | Retrofit + OkHttp |
| **Backend** | Python 3.10+ + FastAPI |
| **LLM** | MiniMax M2.7 |
| **Database** | SQLite |
| **Push** | Feishu OpenAPI, WeChat Work |
| **Search** | Tavily API, V2EX, Hacker News |
| **Weather** | QWeather, Open-Meteo |

## Quick Start

### Android Client

```bash
git clone https://github.com/Dapper-YF/Dapper_Coding.git
cd Dapper_Coding/Dapper_Coding_App
./gradlew assembleDebug
```

### Python Backend

```bash
cd Dapper_Coding_Agent
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
python dapper_coding_agent.py
```

## Screenshots

| Chat | Learn | Onboarding | Profile |
|------|-------|------------|---------|
| AI streaming conversation | Daily learning cards | 18-question survey | User settings & dark mode |

---

<div align="center">

---

</div>

<div align="center">

# 🧠 Learning Scout

### AI 驱动的个人学习生态系统

**全栈智能学习平台 — Android 客户端 + Python 后端 + 企业消息集成**

---

</div>

## 什么是 Learning Scout？

Learning Scout 是一个**全栈 AI 学习助手**，将原生 Android 客户端与 Python 后端结合，提供个性化、AI 驱动的学习体验。这不是 demo — 它面向真实用户设计。

### 核心理念

> **从对话到知识，从知识到掌握。**

每次 AI 对话自动提取知识点，构建可视化知识图谱，并接入间隔重复系统 — 闭环连接学习与记忆。

## 系统架构

```
┌──────────────────────────────────────────────────────────────┐
│                    Android 客户端 (Kotlin)                    │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │ AI 对话  │  │  学习    │  │  知识    │  │  个人中心  │  │
│  │ 流式响应 │  │  每日    │  │  图谱    │  │  设置      │  │
│  │ 多会话   │  │  课程    │  │  力导向  │  │  暗色模式  │  │
│  │ 导出     │  │  卡片    │  │  Canvas  │  │  自动更新  │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬───────┘  │
│       │              │              │              │          │
├───────┴──────────────┴──────────────┴──────────────┴──────────┤
│                 Jetpack Compose + Hilt                        │
│                 Room DB + Retrofit + StateFlow                │
└──────────────────────────┬───────────────────────────────────┘
                           │ JWT 认证
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                  Python 后端 (FastAPI)                        │
│                                                              │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────────┐  │
│  │  对话 API    │  │  学习侦察     │  │  推送引擎        │  │
│  │  /api/chat   │  │  RSS + LLM    │  │  飞书/企业微信   │  │
│  │  流式响应    │  │  摘要打标      │  │  定时推送        │  │
│  └──────┬───────┘  └──────┬────────┘  └──────┬───────────┘  │
│         │                  │                   │              │
│  ┌──────┴──────────────────┴───────────────────┴──────────┐  │
│  │            MiniMax M2.7 大模型 + SQLite                 │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

## 项目结构

```
Learning_Scout/
├── Dapper_Coding_App/          # 📱 Android 客户端 (Kotlin)
│   ├── app/src/main/java/
│   │   └── com/learningscout/app/
│   │       ├── data/           # Room DB、Retrofit、Repository
│   │       ├── domain/         # 用例、模型
│   │       ├── ui/
│   │       │   ├── screens/    # 对话、学习、入职问卷、个人中心
│   │       │   ├── components/ # ChatBubble、UpdateDialog 等
│   │       │   ├── theme/      # Material 3 + 自定义渐变
│   │       │   └── navigation/ # Compose 导航
│   │       └── di/             # Hilt 模块
│   └── SPEC.md                 # 产品规格说明书
│
├── Dapper_Coding_Agent/        # 🐍 Python 后端
│   ├── dapper_coding_agent.py  # 主入口（调度/服务器）
│   ├── api_routes.py           # FastAPI 路由
│   ├── learning_agent.py       # Learning Scout v3 引擎
│   ├── push_engine.py          # 飞书/微信推送
│   ├── memory.py               # SQLite 记忆层
│   ├── admin/                  # Web 管理后台
│   └── .env.example            # 环境变量模板
│
└── README.md
```

## ✨ Android 客户端特色

### 💬 流式 AI 对话
- 逐 token 实时响应显示
- 多会话对话管理
- 导出对话到文件
- 自动滚动 + 平滑动画

### 📚 每日学习内容
- Learning Scout 生成的个性化课程
- AI 生成的摘要卡片
- 主题标签与分类
- 阅读时长预估

### 🎓 入职问卷
- 18 题树状用户画像采集
- 基于答案的自适应问题流
- 构建个性化学习偏好
- DataStore 本地存储

### 🎨 设计系统
- Material Design 3 + 自定义渐变
- 暗色模式切换
- 统一色彩体系（GradientStart → GradientEnd）
- 自定义字体与形状

### 🔄 自动更新
- 内置版本检查器
- 更新日志展示
- 关键版本强制更新
- 跳过版本选项

### 🏗️ 技术亮点
- **MVVM + Clean Architecture** — 清晰的关注点分离
- **Hilt DI** — 编译时依赖注入
- **Room DB** — 离线优先本地存储
- **Retrofit + OkHttp** — 类型安全 HTTP 客户端
- **StateFlow** — 响应式状态管理
- **JWT 自动刷新** — 通过拦截器无感续期

## 🐍 后端特色

### Learning Scout v3
- RSS/Atom 订阅聚合
- LLM 驱动的内容摘要
- 智能标签与分类
- 内容质量反馈闭环
- 系列文章自动检测

### 推送引擎
- 飞书 OpenAPI 集成
- 企业微信 Webhook
- 每日定时简报（08:00）
- 多格式卡片消息

### Web 管理后台
- FastAPI + 静态文件托管
- HTTP Basic Auth 防护
- 推送日志查看器
- 学习内容浏览器

## 技术栈

| 层级 | 技术 |
|------|------|
| **Android UI** | Jetpack Compose + Material 3 |
| **Android 架构** | MVVM + Clean Architecture |
| **Android DI** | Hilt |
| **Android DB** | Room |
| **Android 网络** | Retrofit + OkHttp |
| **后端** | Python 3.10+ + FastAPI |
| **大模型** | MiniMax M2.7 |
| **数据库** | SQLite |
| **推送** | 飞书 OpenAPI、企业微信 |
| **搜索** | Tavily API、V2EX、Hacker News |
| **天气** | 和风天气、Open-Meteo |

## 快速开始

### Android 客户端

```bash
git clone https://github.com/Dapper-YF/Dapper_Coding.git
cd Dapper_Coding/Dapper_Coding_App
./gradlew assembleDebug
```

### Python 后端

```bash
cd Dapper_Coding_Agent
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 填入你的 API 密钥
python dapper_coding_agent.py
```

---

<div align="center">

**Built with ❤️ for lifelong learners**

**为终身学习者而生**

</div>
