# -*- coding: utf-8 -*-
"""
Learning Scout API Routes
为 APP 提供 API 接口（/api/...）

依赖：
- FastAPI StreamingResponse
- Bearer token 认证（dev_token_mvp）
- 复用 learning_agent.py 的消息处理逻辑
- 复用 lesson_generator.py 的知识点提取逻辑

nginx 配置提醒（部署时需添加）：
    # /api/ 路径关闭代理缓存，确保 SSE streaming 正常
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        # 关键：关闭 nginx 缓冲，否则 SSE 会卡住
        proxy_buffering off;
        proxy_cache off;
        # SSE 必须
        X-Accel-Buffering: no;
    }
"""

import json
import logging
import os
import random
import re
import sqlite3
import math
from datetime import datetime, timezone, timedelta
from typing import List, Optional, AsyncGenerator

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse

logger = logging.getLogger(__name__)

# ============================================================
# 常量
# ============================================================

# MVP 阶段硬编码 token，后续改为从环境变量读取
API_TOKEN = os.getenv("API_TOKEN", "dev_token_mvp")

# 项目根目录（兼容本地和 VPS）
def _project_root():
    current = os.path.dirname(os.path.abspath(__file__))
    if os.path.basename(current) == "Dapper_Coding":
        return current
    return os.getcwd()

def _db_path():
    return os.path.join(_project_root(), "dapper_memory.db")

# ============================================================
# 认证依赖（双轨：dev_token_mvp + JWT）
# ============================================================

from onboarding_backend import verify_user  # noqa: E402


def _get_dialogue_manager():
    """懒加载 dialogue_manager"""
    from dialogue_manager import get_dialogue_manager
    return get_dialogue_manager()


# ============================================================
# 知识点提取（复用 lesson_generator.py 的逻辑）
# ============================================================

def _extract_knowledge_points_from_history(history: List[dict]) -> List[str]:
    """
    从对话历史中提取知识点关键词。
    复用 lesson_generator.py 的思路：用 LLM 提取，或用关键词匹配。
    这里先用启发式提取（关键词+短语），后续可替换为 LLM 提取。
    """
    if not history:
        return []

    # 合并对话内容
    all_text = "\n".join(
        f"{turn.get('role', '')}: {turn.get('content', '')}"
        for turn in history
    )

    # 用 LLM 提取知识点（复用 lesson_generator 的 _call_llm）
    try:
        from lesson_generator import _call_llm
        system_prompt = (
            "You are a knowledge point extractor. "
            "From the conversation below, extract 3-8 key programming/technical concepts or知识点. "
            "Return ONLY a JSON array of concept names, e.g. [\"RESTful API\", \"Python list\", \"异步编程\"]. "
            "If no clear concepts, return []. "
            "Language: answer in the same language as the concepts."
        )
        user_prompt = f"Conversation:\n{all_text[:3000]}"
        response = _call_llm(
            [{"role": "system", "content": system_prompt},
             {"role": "user", "content": user_prompt}],
            temperature=0.3,
            max_tokens=300
        )
        # 提取 JSON 数组
        match = re.search(r'\[[\s\S]*\]', response)
        if match:
            points = json.loads(match.group(0))
            return points if isinstance(points, list) else []
    except Exception as exc:
        logger.warning("知识点提取失败（回退到关键词提取）: %s", exc)

    # 回退：启发式关键词提取
    keywords = []
    tech_patterns = [
        r'\b(Python|JavaScript|TypeScript|Java|C\+\+|Go|Rust|Swift|Kotlin)\b',
        r'\b(RESTful|API|Web|Server|Client|Database|SQL|NoSQL)\b',
        r'\b(function|class|module|package|library|framework)\b',
        r'\b(异步|同步|多线程|进程|并发|并行)\b',
        r'\b(变量|函数|对象|数组|字典|列表|元组|字符串|整数|浮点数)\b',
        r'\b(机器学习|深度学习|神经网络|AI|LLM|AGI)\b',
    ]
    for pattern in tech_patterns:
        matches = re.findall(pattern, all_text, re.IGNORECASE)
        keywords.extend([m.strip() for m in matches if len(m.strip()) > 2])
    # 去重
    seen = set()
    unique = []
    for kw in keywords:
        lower = kw.lower()
        if lower not in seen:
            seen.add(lower)
            unique.append(kw)
    return unique[:8]


# ============================================================
# 知识图谱生成
# ============================================================

def _generate_graph_from_points(points: List[str]) -> dict:
    """
    Build nodes + edges graph from knowledge points.
    Double-ring layout: up to 6 inner nodes, rest on outer ring.
    """
    nodes = []
    edges = []

    nodes.append({
        "id": "center",
        "label": "Learning",
        "type": "center",
        "mastery": 1.0,
        "color": "primary",
        "x": 0.5,
        "y": 0.5,
    })

    n = len(points)
    if n == 0:
        return {"nodes": nodes, "edges": edges}

    inner_count = min(n, 6)
    inner_radius = 0.22
    outer_radius = 0.38

    for i, point in enumerate(points):
        point_id = f"node_{i}"
        is_inner = i < inner_count
        idx = i if is_inner else i - inner_count
        total = inner_count if is_inner else n - inner_count
        radius = inner_radius if is_inner else outer_radius
        angle = (2 * math.pi * idx / max(total, 1)) - math.pi / 2
        x = round(0.5 + radius * math.cos(angle), 3)
        y = round(0.5 + radius * math.sin(angle), 3)

        mastery = round(0.3 + (hash(point) % 70) / 100, 2)
        color = "primary" if mastery >= 0.75 else ("secondary" if mastery >= 0.45 else "tertiary")
        nodes.append({
            "id": point_id,
            "label": point,
            "type": "concept",
            "mastery": mastery,
            "color": color,
            "x": x,
            "y": y,
        })
        edges.append({"from": "center", "to": point_id})

    for i in range(min(inner_count - 1, 5)):
        edges.append({"from": f"node_{i}", "to": f"node_{i + 1}"})

    return {"nodes": nodes, "edges": edges}


# ============================================================
# Streaming Chat（复用 learning_agent 逻辑）
# ============================================================

def _generate_insight_chips(context: str, message: str) -> List[str]:
    """
    基于对话上下文生成 3 个推荐跟进问题。
    优先用 LLM 生成，失败时回退到启发式提取。
    """
    try:
        from lesson_generator import _call_llm
        prompt = (
            "You are a learning assistant. Based on the user's question below, "
            "suggest EXACTLY 3 follow-up questions that help the user explore the topic more deeply. "
            "The questions should be in the same language as the user's input.\n\n"
            f"User's question: {message}\n\n"
            "Return ONLY a JSON array of 3 strings, e.g. [\"问题1\", \"问题2\", \"问题3\"]. "
            "Each question max 20 characters. No other text."
        )
        response = _call_llm(
            [{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=200,
        )
        match = re.search(r'\[[\s\S]*\]', response)
        if match:
            chips = json.loads(match.group(0))
            if isinstance(chips, list) and len(chips) >= 1:
                return [c.strip() for c in chips[:3] if c.strip()]
    except Exception as exc:
        logger.warning("生成 insight chips 失败: %s", exc)

    # 回退：基于关键词生成问题
    keywords = _extract_keywords(message)
    if keywords:
        templates = [
            f"请详细解释{keywords[0]}",
            f"{keywords[0]}有哪些应用场景？",
            f"如何深入学习{keywords[0] if len(keywords) == 1 else keywords[1] if len(keywords) > 1 else keywords[0]}？",
        ]
        return templates[:3]
    return []


def _extract_keywords(text: str) -> List[str]:
    """从文本中提取关键词（轻量回退）"""
    # 移除标点，按词分割
    words = re.findall(r'[一-鿿]{2,}|[a-zA-Z]{3,}', text)
    seen = set()
    keywords = []
    for w in words:
        lower = w.lower()
        if lower not in seen and lower not in ('the', 'and', 'for', 'with', 'this', 'that', 'what', 'how', 'why', 'when', 'where', 'can', 'does', 'has', 'are', 'was', 'is', 'been', 'have', '请', '什么', '如何', '怎么', '为什么', '可以', '应该', '是否', '哪些'):
            seen.add(lower)
            keywords.append(w)
        if len(keywords) >= 3:
            break
    return keywords


def _generate_conversation_title(message: str) -> Optional[str]:
    """
    基于用户首条消息生成 10 字内的中文对话标题。
    返回 None 表示生成失败（调用方应采用默认标题）。
    """
    try:
        from lesson_generator import _call_llm
        prompt = (
            "Generate a short title (max 10 Chinese characters, or max 6 English words) "
            "for a conversation that starts with this message. "
            "Return ONLY the title text, nothing else. No quotes, no explanation.\n\n"
            f"Message: {message}"
        )
        title = _call_llm(
            [{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=30,
        )
        title = title.strip().strip('"').strip("'").strip("《").strip("》")
        # 截断过长的标题
        if len(title) > 20:
            title = title[:20]
        return title if title else None
    except Exception as exc:
        logger.warning("生成对话标题失败: %s", exc)
        return None


# ============================================================
# Topic 映射：onboarding answer ID → 可读中文名
# ============================================================

# interest 领域 ID → 中文名
_INTEREST_LABEL_MAP = {
    "cs": "计算机科学",
    "physics": "物理学",
    "math": "数学",
    "other": "其他领域",
}

# interests_detail 子领域 → 中文名
_DETAIL_LABEL_MAP = {
    "artificial_intelligence": "人工智能",
    "machine_learning": "机器学习",
    "deep_learning": "深度学习",
    "nlp": "自然语言处理",
    "computer_vision": "计算机视觉",
    "reinforcement_learning": "强化学习",
    "web_development": "Web 开发",
    "web_frontend": "前端开发",
    "web_backend": "后端开发",
    "full_stack": "全栈开发",
    "backend_development": "后端开发",
    "python_backend": "Python 后端",
    "java_backend": "Java 后端",
    "go_backend": "Go 后端",
    "node_backend": "Node.js 后端",
    "mobile_development": "移动开发",
    "android": "Android 开发",
    "ios": "iOS 开发",
    "cross_platform": "跨平台开发",
    "game_development": "游戏开发",
    "unity": "Unity 开发",
    "unreal": "Unreal 开发",
    "indie_game": "独立游戏开发",
    "algorithms_data_structures": "算法与数据结构",
    "cybersecurity": "网络安全",
    "data_science": "数据科学",
    "mechanics": "力学",
    "electromagnetism": "电磁学",
    "quantum_physics": "量子物理",
    "thermodynamics": "热力学",
    "optics": "光学",
    "relativity": "相对论",
    "calculus": "微积分",
    "linear_algebra": "线性代数",
    "probability_statistics": "概率统计",
    "discrete_math": "离散数学",
    "differential_equations": "微分方程",
    "abstract_algebra": "抽象代数",
    "other_math": "其他数学",
}

# 子领域的简短描述
_TOPIC_DESCRIPTIONS = {
    "机器学习": "掌握监督学习、无监督学习与模型评估的核心方法",
    "深度学习": "理解神经网络、CNN、RNN 与 Transformer 架构",
    "自然语言处理": "探索大语言模型、文本生成与语义理解的前沿技术",
    "计算机视觉": "学习图像识别、目标检测与图像生成技术",
    "强化学习": "从马尔可夫决策过程到深度强化学习算法",
    "人工智能": "覆盖 AI 核心子领域的系统学习路径",
    "前端开发": "React、Vue 等现代框架与响应式设计",
    "后端开发": "API 设计、数据库优化与服务端架构",
    "全栈开发": "前后端贯通，独立完成完整应用",
    "Python 后端": "Django、Flask、FastAPI 快速构建服务",
    "Java 后端": "Spring Boot 企业级应用开发",
    "Go 后端": "高并发微服务与云原生开发",
    "Node.js 后端": "Express、NestJS 全栈 JavaScript 开发",
    "Android 开发": "Kotlin + Jetpack Compose 构建原生应用",
    "iOS 开发": "Swift + SwiftUI 打造 Apple 平台体验",
    "跨平台开发": "Flutter、React Native 一次编写多端运行",
    "游戏开发": "Unity、Unreal 引擎与游戏设计原理",
    "Unity 开发": "C# 脚本、物理引擎与 3D 场景搭建",
    "Unreal 开发": "蓝图系统、C++ 与高性能画面渲染",
    "独立游戏开发": "轻量引擎、像素美术与创意玩法设计",
    "算法与数据结构": "排序、搜索、树、图与动态规划核心思想",
    "网络安全": "渗透测试、密码学与安全防护体系",
    "数据科学": "数据清洗、可视化与统计分析实战",
    "Web 开发": "HTTP 协议、前后端交互与 RESTful API 设计",
    "力学": "牛顿力学、拉格朗日方程与哈密顿体系",
    "电磁学": "麦克斯韦方程组与电磁波传播",
    "量子物理": "波函数、薛定谔方程与量子测量",
    "热力学": "熵、自由能与统计力学基础",
    "光学": "几何光学、波动光学与激光原理",
    "相对论": "狭义与广义相对论的核心思想",
    "微积分": "极限、导数、积分与多变量分析",
    "线性代数": "矩阵、向量空间与特征值分解",
    "概率统计": "概率分布、假设检验与贝叶斯推断",
    "离散数学": "集合论、图论、组合数学与逻辑",
    "微分方程": "常微分方程与偏微分方程的解法",
    "抽象代数": "群、环、域与伽罗瓦理论入门",
    "其他数学": "探索数学的广阔分支与应用",
}


def _get_readable_topics_from_profile(interests: list, interests_detail: dict) -> list:
    """将 onboarding 原始数据转为可读的中文 topic 列表，含层级关系"""
    result = []
    seen = set()

    for interest_id in interests:
        label = _INTEREST_LABEL_MAP.get(interest_id, interest_id)
        if label not in seen:
            result.append({"id": f"area_{interest_id}", "label": label, "type": "branch", "parent": None})
            seen.add(label)

    # 展开 interests_detail 中的子领域
    for area_key, sub_list in interests_detail.items():
        area_label = _DETAIL_LABEL_MAP.get(area_key, area_key)
        for sub in (sub_list if isinstance(sub_list, list) else []):
            sub_label = _DETAIL_LABEL_MAP.get(sub, sub)
            if sub_label not in seen:
                result.append({"id": f"sub_{sub}", "label": sub_label, "type": "leaf", "parent": area_label})
                seen.add(sub_label)

    return result


def _get_all_detected_topics_from_profile(interests: list, interests_detail: dict) -> list:
    """返回所有可检测的 topic 关键词（用于聊天内容匹配）"""
    topics = _get_readable_topics_from_profile(interests, interests_detail)
    return [t["label"] for t in topics]


def _get_default_topics() -> List[dict]:
    """当用户没有 onboarding 数据时的默认主题列表"""
    return [
        {"id": "topic_python", "title": "Python 编程", "description": "从基础语法到高级特性", "mastery": 0.0},
        {"id": "topic_ml", "title": "机器学习入门", "description": "理解监督学习与无监督学习的核心概念", "mastery": 0.0},
        {"id": "topic_web", "title": "Web 开发基础", "description": "HTTP 协议、前后端交互与 RESTful API 设计", "mastery": 0.0},
        {"id": "topic_algo", "title": "算法与数据结构", "description": "排序、搜索、树、图与动态规划", "mastery": 0.0},
        {"id": "topic_db", "title": "数据库与 SQL", "description": "关系模型、查询优化与事务管理", "mastery": 0.0},
        {"id": "topic_os", "title": "操作系统原理", "description": "进程管理、内存管理与文件系统", "mastery": 0.0},
    ]


def _detect_topics_in_response(full_response: str, user_id: str) -> List[str]:
    """
    检测 AI 回复中提到了用户 onboarding 画像中的哪些 topic。
    用于触发前端知识图谱节点高亮。
    """
    try:
        with sqlite3.connect(_db_path()) as conn:
            profile = conn.execute(
                "SELECT interests, interests_detail FROM onboarding_profiles WHERE user_id=?",
                (user_id,)
            ).fetchone()

            if not profile:
                return []

            interests = json.loads(profile["interests"] or "[]")
            interests_detail = json.loads(profile["interests_detail"] or "{}")

        all_topics = _get_all_detected_topics_from_profile(interests, interests_detail)
        detected = []
        for topic in all_topics:
            if topic in full_response:
                detected.append(topic)
        return list(dict.fromkeys(detected))[:5]  # 去重，最多5个
    except Exception as exc:
        logger.warning("Topic detection failed: %s", exc)
        return []


def _stream_chat(user_id: str, message: str, conversation_id: str = None, model: str = None) -> AsyncGenerator[str, None]:
    """
    生成 streaming SSE 响应。
    每个 chunk: "data: {...}\n\n"
    完成: "data: [DONE]\n\n"
    """
    # 延迟导入避免循环依赖


    # 用 LLM API 进行流式响应
    try:
        import requests as _requests

        # 构建消息历史 context
        dm = _get_dialogue_manager()
        context = dm.build_context(user_id, channel="app", limit=10, client_session_id=conversation_id or "")

        # 构造 messages
        messages = []
        if context:
            messages.append({"role": "system", "content": f"对话历史：\n{context}"})
        messages.append({"role": "user", "content": message})

        model = model or os.getenv("LLM_MODEL", "minimax-m2.7")
        url = f"{os.getenv('LLM_BASE_URL', 'https://api.minimax.chat/v1')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {os.getenv('LLM_API_KEY', '')}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "temperature": 0.7,
        }

        full_response = ""

        with _requests.post(url, headers=headers, json=payload, stream=True, timeout=60) as resp:
            if resp.status_code != 200:
                error_text = resp.text
                yield f"data: {json.dumps({'error': f'LLM API error: {resp.status_code}', 'detail': error_text})}\n\n"
                return

            for line in resp.iter_lines(decode_unicode=True):
                if not line:
                    continue
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                        if delta:
                            full_response += delta
                            yield f"data: {json.dumps({'delta': delta, 'partial': full_response}, ensure_ascii=False)}\n\n"
                    except json.JSONDecodeError:
                        continue

        # 保存对话历史
        user_timestamp = None
        ai_timestamp = None
        try:
            dm = _get_dialogue_manager()
            # 判断是否为首条消息（存标题）
            is_first = dm.message_count(user_id, "app", client_session_id=conversation_id or "") == 0
            dm.add_user_message(user_id, "app", message, client_session_id=conversation_id or "")
            dm.add_assistant_message(user_id, "app", full_response, client_session_id=conversation_id or "")

            # 获取保存后的时间戳
            now_iso = datetime.now(timezone(timedelta(hours=8))).isoformat()
            user_timestamp = now_iso
            ai_timestamp = now_iso

            # 首条消息时生成标题
            title = None
            if is_first:
                title = _generate_conversation_title(message)
                if title:
                    dm.set_title(user_id, "app", title, client_session_id=conversation_id or "")
        except Exception as exc:
            logger.warning("保存对话历史失败: %s", exc)

        # 生成 insight_chips
        insight_chips = _generate_insight_chips("", message)

        # 检测 AI 回复中涉及的用户画像 topic
        detected_topics = _detect_topics_in_response(full_response, user_id)

        done_data = {
            "done": True,
            "full": full_response,
            "timestamp": ai_timestamp or datetime.now(timezone(timedelta(hours=8))).isoformat(),
            "user_timestamp": user_timestamp or datetime.now(timezone(timedelta(hours=8))).isoformat(),
            "insight_chips": insight_chips,
            "detected_topics": detected_topics,
        }
        yield f"data: {json.dumps(done_data, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    except Exception as exc:
        logger.error("Streaming chat error: %s", exc)
        yield f"data: {json.dumps({'error': str(exc)})}\n\n"


# ============================================================
# 数据模型
# ============================================================

# ============================================================
# API Routes
# ============================================================

router = APIRouter(prefix="/api")


@router.post("/chat")
async def api_chat(
    request: Request,
    authorization: str = Header(...),
):
    """
    Streaming Chat API

    Request body (JSON):
        conversation_id: str (optional, for future use)
        message: str (required)
        model: str (optional, default from env LLM_MODEL)

    Response: text/event-stream (SSE)
        data: {"delta": "...", "partial": "..."}
        data: {"done": true, "full": "..."}

    nginx 配置提醒:
        proxy_buffering off;
        proxy_cache off;
        X-Accel-Buffering: no;
    """
    user_id = verify_user(authorization)

    body = await request.json()
    message = body.get("message", "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="message is required")
    model = body.get("model")
    # conversation_id 用于关联已有会话
    conversation_id = body.get("conversation_id")

    return StreamingResponse(
        _stream_chat(user_id, message, conversation_id, model),
        media_type="text/event-stream",
        headers={
            # nginx SSE 必需
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.post("/graph/generate")
async def api_graph_generate(
    request: Request,
    authorization: str = Header(...),
):
    """
    生成知识图谱

    Request body (JSON):
        conversation_id: str (required)

    Response:
        {
            "nodes": [
                {"id": "...", "label": "...", "type": "concept|center", "mastery": 0.0-1.0, "color": "primary|secondary|tertiary", "x": 0.0-1.0, "y": 0.0-1.0}
            ],
            "edges": [
                {"from": "...", "to": "..."}
            ]
        }

    逻辑：
        1. 从 dialogue_turns 取对话历史
        2. 用 LLM 提取知识点（复用 lesson_generator 逻辑）
        3. 生成 nodes + edges（x/y 由 Backend 计算好圆形布局）
    """
    user_id = verify_user(authorization)

    body = await request.json()
    conversation_id = body.get("conversation_id", "").strip()
    if not conversation_id:
        raise HTTPException(status_code=400, detail="conversation_id is required")

    try:
        dm = _get_dialogue_manager()

        session_id = int(conversation_id) if conversation_id.isdigit() else None

        if session_id is not None:
            with sqlite3.connect(_db_path()) as conn:
                row = conn.execute(
                    "SELECT id FROM dialogue_sessions WHERE id=? AND user_id=? AND channel='app'",
                    (session_id, user_id),
                ).fetchone()
                if row:
                    turns = conn.execute(
                        "SELECT role, content FROM dialogue_turns WHERE session_id=? ORDER BY created_at ASC LIMIT 50",
                        (session_id,)
                    ).fetchall()
                    history = [{"role": role, "content": content} for role, content in turns]
                else:
                    history = []
        else:
            history = []
            if profile:
                interests = json.loads(profile["interests"] or "[]")
                interests_detail = json.loads(profile["interests_detail"] or "{}")
                topic_tree = _get_readable_topics_from_profile(interests, interests_detail)
                if topic_tree:
                    topic_points = [t["label"] for t in topic_tree]
                    return _generate_graph_from_points(topic_points)

            return JSONResponse({
                "nodes": [
                    {"id": "center", "label": "开始对话以生成图谱", "type": "center", "mastery": 1.0, "color": "primary", "x": 0.5, "y": 0.5}
                ],
                "edges": []
            })

        # 提取知识点
        points = _extract_knowledge_points_from_history(history)

        # 合并 onboarding 画像中的兴趣主题
        with sqlite3.connect(_db_path()) as conn:
            profile = conn.execute(
                "SELECT interests, interests_detail FROM onboarding_profiles WHERE user_id=?",
                (user_id,)
            ).fetchone()
        if profile:
            try:
                profile_interests = json.loads(profile["interests"] or "[]")
                profile_detail = json.loads(profile["interests_detail"] or "{}")
                profile_topics = _get_all_detected_topics_from_profile(profile_interests, profile_detail)
                all_points = list(dict.fromkeys(profile_topics + points))
                points = all_points
            except Exception:
                pass

        if not points:
            points = ["Learning"]

        graph = _generate_graph_from_points(points)
        return JSONResponse(graph)

    except Exception as exc:
        logger.error("Graph generate error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/conversations")
async def api_conversations(
    authorization: str = Header(...),
):
    """
    获取所有会话列表

    Response:
        [
            {
                "id": 1,
                "user_id": "user_001",
                "channel": "app",
                "title": "量子计算入门",
                "created_at": "2026-05-01T12:00:00",
                "last_active": "2026-05-01T14:30:00",
                "message_count": 10
            },
            ...
        ]
    """
    user_id = verify_user(authorization)

    try:
        with sqlite3.connect(_db_path()) as conn:
            rows = conn.execute("""
                SELECT
                    s.id,
                    s.user_id,
                    s.channel,
                    s.title,
                    s.created_at,
                    s.last_active,
                    COUNT(t.id) as message_count
                FROM dialogue_sessions s
                LEFT JOIN dialogue_turns t ON t.session_id = s.id
                WHERE s.channel = 'app' AND s.user_id = ?
                GROUP BY s.id
                ORDER BY s.last_active DESC
                LIMIT 100
            """, (user_id,)).fetchall()

        result = [
            {
                "id": row[0],
                "user_id": row[1],
                "channel": row[2],
                "title": row[3] or "",
                "created_at": row[4],
                "last_active": row[5],
                "message_count": row[6],
            }
            for row in rows
        ]
        return result

    except Exception as exc:
        logger.error("List conversations error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/conversations/{conversation_id}/history")
async def api_conversation_history(
    conversation_id: str,
    authorization: str = Header(...),
):
    """
    获取单个会话的完整消息历史

    Response:
        [
            {"role": "user", "content": "...", "created_at": "..."},
            {"role": "assistant", "content": "...", "created_at": "..."},
            ...
        ]
    """
    user_id = verify_user(authorization)

    try:
        with sqlite3.connect(_db_path()) as conn:
            session_id = int(conversation_id) if conversation_id.isdigit() else None
            if session_id is None:
                raise HTTPException(status_code=400, detail="Invalid conversation_id")

            # Verify the session belongs to this user
            row = conn.execute(
                "SELECT id FROM dialogue_sessions WHERE id=? AND user_id=? AND channel='app'",
                (session_id, user_id),
            ).fetchone()

            if not row:
                raise HTTPException(status_code=404, detail="Conversation not found")

            turns = conn.execute(
                "SELECT role, content, created_at FROM dialogue_turns WHERE session_id=? ORDER BY created_at ASC",
                (session_id,)
            ).fetchall()

        result = [
            {"role": role, "content": content, "created_at": created_at}
            for role, content, created_at in turns
        ]
        return result

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Conversation history error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/conversations/{conversation_id}")
async def api_delete_conversation(
    conversation_id: str,
    authorization: str = Header(...),
):
    """删除指定会话及其所有对话记录"""
    user_id = verify_user(authorization)

    try:
        with sqlite3.connect(_db_path()) as conn:
            row = conn.execute(
                "SELECT id FROM dialogue_sessions WHERE user_id=? AND channel='app' AND id=?",
                (user_id, conversation_id),
            ).fetchone()

            if not row:
                raise HTTPException(status_code=404, detail="Conversation not found")

            session_id = row[0]
            conn.execute("DELETE FROM dialogue_turns WHERE session_id=?", (session_id,))
            conn.execute("DELETE FROM dialogue_sessions WHERE id=?", (session_id,))
            conn.commit()

        logger.info("User %s deleted conversation %s", user_id, conversation_id)
        return {"status": "deleted", "conversation_id": conversation_id}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Delete conversation error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/user/stats")
async def api_user_stats(
    authorization: str = Header(...),
):
    """
    获取用户学习统计

    Response:
        {
            "username": "用户真名",
            "days_learning": 42,
            "concepts_mastered": 128,
            "active_days": 30,
            "current_streak": 14
        }
    """
    user_id = verify_user(authorization)

    try:
        with sqlite3.connect(_db_path()) as conn:
            # 查询用户名
            user_row = conn.execute(
                "SELECT name FROM users WHERE user_id=?", (user_id,)
            ).fetchone()
            username = user_row[0] if user_row and user_row[0] else (user_id if user_id != "admin" else "管理员")

            # total_messages
            msg_row = conn.execute("""
                SELECT COUNT(t.id)
                FROM dialogue_sessions s
                JOIN dialogue_turns t ON t.session_id = s.id
                WHERE s.channel = 'app' AND s.user_id = ?
            """, (user_id,)).fetchone()
            total_messages = msg_row[0] if msg_row else 0

            # days_learning
            first_session = conn.execute("""
                SELECT MIN(created_at) FROM dialogue_sessions
                WHERE channel = 'app' AND user_id = ?
            """, (user_id,)).fetchone()[0]
            if first_session:
                first_date = datetime.fromisoformat(first_session)
                days_learning = (datetime.now() - first_date).days + 1
            else:
                days_learning = 0

            # current_streak & active_days
            streak = 0
            active_days = 0
            for i in range(30):
                check_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                check_date = check_date.replace(day=max(1, check_date.day - i))
                day_start = check_date.strftime('%Y-%m-%d')
                day_count = conn.execute("""
                    SELECT COUNT(*) FROM dialogue_turns t
                    JOIN dialogue_sessions s ON s.id = t.session_id
                    WHERE s.channel = 'app' AND s.user_id = ? AND date(t.created_at) = date(?)
                """, (user_id, day_start)).fetchone()[0]
                if day_count > 0:
                    active_days += 1
                    if i == streak:
                        streak += 1
                elif i < 1:
                    break  # only break streak on 2nd+ consecutive miss

            # concepts_mastered: 从 mastery_records 表统计 mastery >= 0.6 的概念数
            mastery_row = conn.execute("""
                SELECT COUNT(*) FROM mastery_records
                WHERE user_id = ? AND mastery_score >= 0.6
            """, (user_id,)).fetchone()
            concepts_mastered = mastery_row[0] if mastery_row else 0

        return {
            "username": username,
            "days_learning": days_learning,
            "concepts_mastered": concepts_mastered,
            "active_days": active_days,
            "current_streak": streak,
        }

    except Exception as exc:
        logger.error("User stats error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/digest/latest")
async def api_latest_digest(
    authorization: str = Header(...),
):
    """
    获取用户最新的 Tech Digest

    Response:
        {
            "digest": {
                "id": 1,
                "date": "2026-05-05",
                "title": "今日 AI 速报",
                "content": "...",
                "source_articles": "...",
                "created_at": "2026-05-05 08:10:00"
            }
        }
        如果没有 digest 记录，返回 {"digest": null}
    """
    user_id = verify_user(authorization)

    try:
        from memory import get_latest_digest
        digest = get_latest_digest(user_id)
        if not digest:
            return {"digest": None}
        return {
            "digest": {
                "id": digest.id,
                "date": digest.push_date,
                "title": digest.title,
                "content": digest.content,
                "source_articles": digest.source_articles,
                "created_at": digest.created_at,
            }
        }
    except Exception as exc:
        logger.error("Latest digest error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/discover")
async def api_discover(authorization: str = Header(...)):
    """
    获取发现页推荐话题列表（基于 onboarding 个性化）

    读取用户的 onboarding_answers，提取用户已选的 topics，
    只返回这些 topics 下的子话题。
    如果还没开始学习，返回 onboarding 推荐的入门 topic。

    Response:
        {
            "topics": [
                {"id": "sub_xxx", "title": "机器学习", "description": "...", "mastery": 0.0},
                ...
            ]
        }
    """
    user_id = verify_user(authorization)

    try:
        with sqlite3.connect(_db_path()) as conn:
            # 读取 onboarding 画像
            profile = conn.execute(
                "SELECT interests, interests_detail, onboarding_complete FROM onboarding_profiles WHERE user_id=?",
                (user_id,)
            ).fetchone()

            interests = []
            interests_detail = {}
            onboarding_complete = False
            if profile:
                try:
                    interests = json.loads(profile["interests"] or "[]")
                    interests_detail = json.loads(profile["interests_detail"] or "{}")
                except (json.JSONDecodeError, TypeError):
                    pass
                onboarding_complete = bool(profile["onboarding_complete"])

            # 读取 mastery 数据
            conn.execute("""
                CREATE TABLE IF NOT EXISTS mastery_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    mastery_score REAL DEFAULT 0.0,
                    updated_at TEXT NOT NULL,
                    UNIQUE(user_id, topic)
                )
            """)
            conn.commit()

            mastery_rows = conn.execute(
                "SELECT topic, mastery_score FROM mastery_records WHERE user_id=?",
                (user_id,)
            ).fetchall()
            mastery_map = {row[0]: row[1] for row in mastery_rows}

        topics = []

        if onboarding_complete and (interests or interests_detail):
            # 从 onboarding 数据提取子话题
            topic_tree = _get_readable_topics_from_profile(interests, interests_detail)
            for t in topic_tree:
                label = t["label"]
                # 优先取叶子节点（具体子领域），但也包含分支节点
                desc = _TOPIC_DESCRIPTIONS.get(label, f"探索「{label}」的核心概念与应用场景")
                m = mastery_map.get(label, 0.0)
                topics.append({
                    "id": t["id"],
                    "title": label,
                    "description": desc,
                    "mastery": round(m, 2),
                })

        # 按 mastery 升序排列（未开始的排在前面）
        topics.sort(key=lambda t: t["mastery"])

        if not topics:
            # 用户尚未完成问卷
            return {"topics": [], "empty_reason": "onboarding_required"}

        return {"topics": topics[:20]}

    except Exception as exc:
        logger.error("Discover error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


def _describe_topic(topic: str) -> str:
    """简单的 topic 描述映射"""
    descriptions = {
        "Python": "从基础语法到高级特性，掌握 Python 编程",
        "JavaScript": "前端与全栈开发的核心语言",
        "机器学习": "理解监督学习与无监督学习的核心方法",
        "深度学习": "神经网络、CNN、RNN 与 Transformer 架构",
        "算法": "排序、搜索、动态规划等核心算法思想",
        "数据结构": "数组、链表、树、图与哈希表",
        "API": "RESTful API 设计与最佳实践",
        "数据库": "SQL 查询、索引优化与事务管理",
        "HTTP": "HTTP 协议、状态码与缓存策略",
        "Git": "版本控制与团队协作工作流",
        "Docker": "容器化部署与微服务架构",
    }
    for key, desc in descriptions.items():
        if key.lower() in topic.lower():
            return desc
    return f"探索 {topic} 的核心概念与应用场景"


@router.get("/graph")
async def api_graph(authorization: str = Header(...)):
    """
    获取用户知识图谱（基于 onboarding 个性化定制）

    读取 onboarding_profiles 表，提取用户选择的领域和子领域，
    生成只包含这些领域的知识节点图谱。

    Response:
        {
            "nodes": [
                {"id": "...", "label": "...", "type": "center|branch|leaf", "mastery": 0.0-1.0, "x": 0.0-1.0, "y": 0.0-1.0},
                ...
            ],
            "edges": [{"from": "...", "to": "..."}]
        }
    """
    user_id = verify_user(authorization)

    try:
        with sqlite3.connect(_db_path()) as conn:
            # 确保 mastery_records 表存在
            conn.execute("""
                CREATE TABLE IF NOT EXISTS mastery_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    mastery_score REAL DEFAULT 0.0,
                    updated_at TEXT NOT NULL,
                    UNIQUE(user_id, topic)
                )
            """)
            conn.commit()

            # 读取 onboarding 完整画像
            profile = conn.execute(
                "SELECT interests, interests_detail, onboarding_complete FROM onboarding_profiles WHERE user_id=?",
                (user_id,)
            ).fetchone()

            interests = []
            interests_detail = {}
            onboarding_complete = False
            if profile:
                try:
                    interests = json.loads(profile["interests"] or "[]")
                    interests_detail = json.loads(profile["interests_detail"] or "{}")
                except (json.JSONDecodeError, TypeError):
                    pass
                onboarding_complete = bool(profile["onboarding_complete"])

            # 从 mastery_records 读取掌握度
            mastery_rows = conn.execute(
                "SELECT topic, mastery_score FROM mastery_records WHERE user_id=?",
                (user_id,)
            ).fetchall()
            mastery_map = {row[0]: row[1] for row in mastery_rows}

        # 将 onboarding 数据转为可读的 topic 层级
        topic_tree = _get_readable_topics_from_profile(interests, interests_detail)

        if not topic_tree:
            # 没有 onboarding 数据：返回空图谱提示
            return {
                "nodes": [{
                    "id": "center",
                    "label": "完成问卷后解锁你的知识图谱",
                    "type": "center",
                    "mastery": 1.0,
                    "x": 0.5,
                    "y": 0.5,
                }],
                "edges": [],
            }

        # 构建节点
        nodes = [{
            "id": "center",
            "label": "学习图谱",
            "type": "center",
            "mastery": 1.0,
            "x": 0.5,
            "y": 0.5,
        }]
        edges = []

        # 分支节点（领域级）放在内圈
        branches = [t for t in topic_tree if t["type"] == "branch"]
        leaves = [t for t in topic_tree if t["type"] == "leaf"]

        branch_radius = 0.22
        for i, branch in enumerate(branches[:6]):
            angle = (2 * math.pi * i / max(len(branches[:6]), 1)) - math.pi / 2
            x = round(0.5 + branch_radius * math.cos(angle), 3)
            y = round(0.5 + branch_radius * math.sin(angle), 3)
            m = round(mastery_map.get(branch["label"], 0.0), 2)
            nodes.append({
                "id": branch["id"],
                "label": branch["label"],
                "type": "branch",
                "mastery": m,
                "x": x,
                "y": y,
            })
            edges.append({"from": "center", "to": branch["id"]})

        # 叶子节点（子领域）放在外圈
        leaf_radius = 0.40
        for i, leaf in enumerate(leaves[:12]):
            angle = (2 * math.pi * i / max(len(leaves[:12]), 1)) - math.pi / 2
            x = round(0.5 + leaf_radius * math.cos(angle), 3)
            y = round(0.5 + leaf_radius * math.sin(angle), 3)
            m = round(mastery_map.get(leaf["label"], 0.0), 2)
            nodes.append({
                "id": leaf["id"],
                "label": leaf["label"],
                "type": "leaf",
                "mastery": m,
                "x": x,
                "y": y,
            })
            # 叶节点连接到其父分支
            parent_branch = next((b for b in branches if b["label"] == leaf.get("parent")), None)
            if parent_branch:
                edges.append({"from": parent_branch["id"], "to": leaf["id"]})
            else:
                edges.append({"from": "center", "to": leaf["id"]})

        return {"nodes": nodes, "edges": edges}

    except Exception as exc:
        logger.error("Graph error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/lesson/feedback")
async def api_lesson_feedback(
    request: Request,
    authorization: str = Header(...),
):
    """
    接收课程反馈

    Request body (JSON):
        lesson_id: str (required)
        feedback: str (required) — "mastered" | "learning" | "confused"

    Response:
        {"status": "ok"}

    数据存储到 dapper_memory.db 的 lesson_feedback 表
    """
    verify_user(authorization)

    body = await request.json()
    lesson_id = body.get("lesson_id", "").strip()
    feedback = body.get("feedback", "").strip()

    if not lesson_id or not feedback:
        raise HTTPException(status_code=400, detail="lesson_id and feedback are required")
    if feedback not in ("mastered", "learning", "confused"):
        raise HTTPException(status_code=400, detail="feedback must be mastered|learning|confused")

    try:
        with sqlite3.connect(_db_path()) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS lesson_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lesson_id TEXT NOT NULL,
                    feedback TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute(
                "INSERT INTO lesson_feedback (lesson_id, feedback, created_at) VALUES (?, ?, ?)",
                (lesson_id, feedback, datetime.now().isoformat())
            )

        logger.info(f"Lesson feedback: lesson={lesson_id}, feedback={feedback}")
        return {"status": "ok"}

    except Exception as exc:
        logger.error("Lesson feedback error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/chat/summarize")
async def api_chat_summarize(
    request: Request,
    authorization: str = Header(...),
):
    """
    对话摘要 API

    Request body (JSON):
        conversation_id: str (required)

    Response:
        {
            "summary": "本次对话的核心内容摘要...",
            "key_points": ["知识点1", "知识点2", "知识点3"],
            "next_topics": ["推薦下一步学习方向1", "方向2"]
        }

    逻辑：
        1. 从 dialogue_turns 读取对话历史
        2. 用 LLM 总结对话内容
        3. 返回结构化摘要
    """
    user_id = verify_user(authorization)

    body = await request.json()
    conversation_id = body.get("conversation_id", "").strip()
    if not conversation_id:
        raise HTTPException(status_code=400, detail="conversation_id is required")

    try:
        dm = _get_dialogue_manager()

        with sqlite3.connect(_db_path()) as conn:
            # 查找 session
            row = conn.execute(
                "SELECT id FROM dialogue_sessions WHERE user_id=? AND channel='app' LIMIT 1",
                (conversation_id,)
            ).fetchone()

            if not row:
                session_id = int(conversation_id) if conversation_id.isdigit() else 1
            else:
                session_id = row[0]

            turns = conn.execute(
                "SELECT role, content FROM dialogue_turns WHERE session_id=? ORDER BY created_at ASC LIMIT 50",
                (session_id,)
            ).fetchall()

        history = [{"role": role, "content": content} for role, content in turns]

        if not history:
            return JSONResponse({
                "summary": "暂无对话内容",
                "key_points": [],
                "next_topics": [],
            })

        # 用 LLM 生成摘要
        try:
            from lesson_generator import _call_llm

            # 构建对话文本
            conversation_text = "\n".join(
                f"{'用户' if t['role'] == 'user' else 'AI'}: {t['content'][:500]}"
                for t in history
            )

            system_prompt = (
                "你是一个学习助手。请根据以下对话内容，生成一份简洁的学习摘要。\n"
                "返回严格的 JSON 格式，不要包含其他文字：\n"
                '{"summary": "对话核心内容摘要（100字以内）", '
                '"key_points": ["关键知识点1", "关键知识点2", "关键知识点3"], '
                '"next_topics": ["推荐下一步学习方向1", "方向2"]}\n'
                "key_points 提取 2-5 个关键知识点，next_topics 推荐 2-3 个可继续深入的方向。"
            )

            user_prompt = f"对话内容：\n{conversation_text[:4000]}"

            response = _call_llm(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.5,
                max_tokens=500,
            )

            # 解析 JSON
            match = re.search(r'\{[\s\S]*\}', response)
            if match:
                result = json.loads(match.group(0))
                return JSONResponse({
                    "summary": result.get("summary", ""),
                    "key_points": result.get("key_points", []),
                    "next_topics": result.get("next_topics", []),
                })
        except Exception as llm_exc:
            logger.warning("LLM 摘要生成失败，使用本地提取: %s", llm_exc)

        # 回退：本地简单提取
        all_user_messages = [t["content"] for t in history if t["role"] == "user"]
        all_ai_messages = [t["content"] for t in history if t["role"] == "assistant"]

        # 提取关键词作为 key_points
        all_text = " ".join(all_user_messages + all_ai_messages[:3])
        keywords = _extract_keywords(all_text)
        key_points = keywords[:5] if keywords else ["对话交流"]

        # 简单摘要
        summary = f"本次对话共 {len(history)} 条消息，讨论了 {'、'.join(key_points[:3]) if keywords else '学习相关内容'}"
        if len(summary) > 100:
            summary = summary[:97] + "..."

        return JSONResponse({
            "summary": summary,
            "key_points": key_points,
            "next_topics": [f"深入了解{k}" for k in key_points[:3]] if key_points else [],
        })

    except Exception as exc:
        logger.error("Summarize error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/lesson/recommend")
async def api_lesson_recommend(
    authorization: str = Header(...),
):
    """
    获取今日推荐课程

    Response:
        {
            "lesson": {
                "id": "daily_2026_05_02",
                "title": "量子纠缠入门",
                "summary": "...",
                "key_insight": "...",
                "image_url": "..."
            },
            "review_lesson": {
                "id": "review_...",
                "title": "..."
            }
        }

    策略：
        - 新课：从用户未掌握的知识点中选一个，生成课程
        - 复习课：从 lesson_feedback 中找 "learning" 或 "confused" 的 lesson_id
        - 缓存：同一天同一个 user 优先返回缓存
    """
    verify_user(authorization)

    today = datetime.now().strftime("%Y-%m-%d")
    default_lesson = {
        "id": f"daily_{today}",
        "title": "量子纠缠入门",
        "summary": "量子纠缠是量子力学中最神奇的现象之一，两个粒子可以处于相互关联的状态...",
        "key_insight": "量子纠缠不是瞬时通信，而是一种非经典的关联",
        "image_url": ""
    }

    try:
        with sqlite3.connect(_db_path()) as conn:
            # 查找需要复习的内容
            rows = conn.execute("""
                SELECT DISTINCT lesson_id, feedback, created_at
                FROM lesson_feedback
                WHERE feedback IN ('learning', 'confused')
                ORDER BY created_at DESC
                LIMIT 1
            """).fetchall()

        review_lesson = None
        if rows:
            review_id, fb, created = rows[0]
            review_lesson = {
                "id": review_id,
                "title": f"复习: {review_id}",
            }

        return {
            "lesson": default_lesson,
            "review_lesson": review_lesson,
        }

    except Exception as exc:
        logger.error("Lesson recommend error: %s", exc)
        return {"lesson": default_lesson, "review_lesson": None}


