# -*- coding: utf-8 -*-
"""
Learning Scout Onboarding Backend
用户成长体系：注册/登录 → 树状问卷 → 人设管理

依赖：
- api_routes.py 中的 verify_bearer（兼容 dev_token_mvp）
- dapper_memory.db（主数据库）
- PyJWT（pip install pyjwt）

API 路由挂载到 /api 前缀（与 api_routes.py 共享 router）

Phase 1: 数据库 + Auth
Phase 2: 问卷系统
Phase 3: 人设 API + LA 集成
"""

import json
import logging
import os
import re
import sqlite3
import secrets
from datetime import datetime, timedelta

import jwt
from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

logger = logging.getLogger(__name__)

# ============================================================
# 常量
# ============================================================

JWT_SECRET = os.getenv("JWT_SECRET", "learning_scout_jwt_secret_2026")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 72  # 3 天过期

# MVP 阶段硬编码 token（与 api_routes.py 保持一致）
API_TOKEN = os.getenv("API_TOKEN", "dev_token_mvp")

ONBOARDING_JSON_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "onboarding_survey.json"
)


def _db_path():
    """数据库路径（复用 dapper_memory.db）"""
    current = os.path.dirname(os.path.abspath(__file__))
    if os.path.basename(current) == "Dapper_Coding":
        return os.path.join(current, "dapper_memory.db")
    return os.path.join(os.getcwd(), "dapper_memory.db")


def _get_db() -> sqlite3.Connection:
    """获取数据库连接（row_factory = dict）"""
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


# ============================================================
# Phase 1: 数据库初始化
# ============================================================

def init_onboarding_db():
    """初始化 onboarding 相关表结构"""
    conn = _get_db()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                device_id TEXT NOT NULL UNIQUE,
                registered_at TEXT NOT NULL,
                last_active_at TEXT NOT NULL
            )
        """)
        # Phase 4: email auth migration
        for col, col_def in [
            ("email", "TEXT"),
            ("password_hash", "TEXT"),
            ("name", "TEXT DEFAULT ''"),
            ("phone", "TEXT DEFAULT ''"),
            ("avatar_url", "TEXT DEFAULT ''"),
            ("email_registered", "INTEGER DEFAULT 0"),
        ]:
            try:
                conn.execute(f"ALTER TABLE users ADD COLUMN {col} {col_def}")
            except sqlite3.OperationalError:
                pass  # column already exists
        conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email)
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS onboarding_profiles (
                user_id TEXT PRIMARY KEY,
                identity TEXT DEFAULT '',
                identity_detail TEXT DEFAULT '',
                interests TEXT DEFAULT '[]',
                interests_detail TEXT DEFAULT '{}',
                skill_levels TEXT DEFAULT '{}',
                unsure_topics TEXT DEFAULT '[]',
                learning_goals TEXT DEFAULT '[]',
                onboarding_complete INTEGER DEFAULT 0,
                raw_answers TEXT DEFAULT '[]',
                onboarding_version TEXT DEFAULT '1.0',
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        conn.commit()
        logger.info("onboarding 表初始化完成")
    except Exception as exc:
        logger.error("onboarding 表初始化失败: %s", exc)
        raise
    finally:
        conn.close()


# ============================================================
# Phase 1: JWT 工具函数
# ============================================================

def generate_user_id() -> str:
    """生成 user_id: "dev_" + 12 位十六进制"""
    return "dev_" + secrets.token_hex(6)


def create_jwt(user_id: str, device_id: str = "", email: str = "") -> str:
    """为用户创建 JWT"""
    payload = {
        "user_id": user_id,
        "device_id": device_id,
        "email": email,
        "is_admin": False,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def decode_jwt(token: str) -> dict:
    """解码 JWT，失败时抛出异常"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ============================================================
# Phase 1: 双轨认证中间件
# ============================================================

def verify_user(authorization: str = Header(...)) -> str:
    """
    双轨认证：兼容 dev_token_mvp 和 JWT

    返回 user_id（对 admin token 返回 "admin"）
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = authorization[7:]

    # 轨道 1: dev_token_mvp（管理员）
    if token == API_TOKEN:
        return "admin"

    # 轨道 2: JWT
    try:
        payload = decode_jwt(token)
        return payload.get("user_id", "")
    except HTTPException:
        raise


# ============================================================
# Phase 1: Auth API
# ============================================================

router = APIRouter(prefix="/api")


@router.post("/auth/register")
async def api_register(request: Request):
    """
    设备 ID 注册

    Request:
        {"device_id": "uuid-of-device"}

    Response:
        {
            "user_id": "dev_xxxxxx",
            "token": "jwt...",
            "new_user": true,
            "onboarding_complete": false
        }
    """
    body = await request.json()
    device_id = (body.get("device_id") or "").strip()
    if not device_id:
        raise HTTPException(status_code=400, detail="device_id is required")

    now = datetime.now().isoformat()
    conn = _get_db()
    try:
        existing = conn.execute(
            "SELECT user_id FROM users WHERE device_id = ?",
            (device_id,)
        ).fetchone()

        new_user = False
        if existing:
            user_id = existing["user_id"]
            conn.execute(
                "UPDATE users SET last_active_at = ? WHERE user_id = ?",
                (now, user_id)
            )
        else:
            user_id = generate_user_id()
            conn.execute(
                "INSERT INTO users (user_id, device_id, registered_at, last_active_at) VALUES (?, ?, ?, ?)",
                (user_id, device_id, now, now)
            )
            conn.execute(
                "INSERT INTO onboarding_profiles (user_id, updated_at) VALUES (?, ?)",
                (user_id, now)
            )
            new_user = True

        conn.commit()

        profile = conn.execute(
            "SELECT onboarding_complete FROM onboarding_profiles WHERE user_id = ?",
            (user_id,)
        ).fetchone()
        onboarding_complete = bool(profile and profile["onboarding_complete"])

        token = create_jwt(user_id, device_id)

        return {
            "user_id": user_id,
            "token": token,
            "new_user": new_user,
            "onboarding_complete": onboarding_complete,
        }
    except Exception as exc:
        logger.error("Register error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        conn.close()


@router.post("/auth/login")
async def api_login(request: Request):
    """
    登录

    Request:
        {"device_id": "uuid-of-device", "user_id": "dev_xxxxxx" (optional)}

    Response:
        {
            "user_id": "dev_xxxxxx",
            "token": "jwt...",
            "onboarding_complete": true/false
        }
    """
    body = await request.json()
    device_id = (body.get("device_id") or "").strip()
    user_id_hint = (body.get("user_id") or "").strip()

    if not device_id:
        raise HTTPException(status_code=400, detail="device_id is required")

    now = datetime.now().isoformat()
    conn = _get_db()
    try:
        existing = conn.execute(
            "SELECT user_id FROM users WHERE device_id = ?",
            (device_id,)
        ).fetchone()

        if not existing:
            raise HTTPException(status_code=404, detail="Device not registered")

        user_id = existing["user_id"]

        if user_id_hint and user_id_hint != user_id:
            raise HTTPException(status_code=403, detail="user_id mismatch")

        conn.execute(
            "UPDATE users SET last_active_at = ? WHERE user_id = ?",
            (now, user_id)
        )
        conn.commit()

        profile = conn.execute(
            "SELECT onboarding_complete FROM onboarding_profiles WHERE user_id = ?",
            (user_id,)
        ).fetchone()
        onboarding_complete = bool(profile and profile["onboarding_complete"])

        token = create_jwt(user_id, device_id)

        return {
            "user_id": user_id,
            "token": token,
            "onboarding_complete": onboarding_complete,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Login error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        conn.close()


@router.post("/auth/register-email")
async def api_register_email(request: Request):
    """
    邮箱注册

    Request:
        {"name": "显示名称", "email": "user@example.com", "password": "明文密码"}

    Response:
        {"token": "jwt...", "user_id": "uuid", "new_user": true}
    Errors: 400 (email格式错), 409 (email已注册)
    """
    body = await request.json()
    email = (body.get("email") or "").strip().lower()
    name = (body.get("name") or "").strip()
    password = (body.get("password") or "")

    if not email or not _EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="邮箱格式不正确")
    if not name:
        raise HTTPException(status_code=400, detail="请输入你的名字")
    if not password or len(password) < 6:
        raise HTTPException(status_code=400, detail="密码至少需要 6 位")

    now = datetime.now().isoformat()
    conn = _get_db()
    try:
        existing = conn.execute(
            "SELECT user_id FROM users WHERE email = ?", (email,)
        ).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="该邮箱已注册")

        user_id = generate_user_id()
        device_id = "email_" + user_id
        password_hash = pwd_context.hash(password)

        conn.execute("""
            INSERT INTO users (user_id, device_id, email, password_hash, name,
                               email_registered, registered_at, last_active_at)
            VALUES (?, ?, ?, ?, ?, 1, ?, ?)
        """, (user_id, device_id, email, password_hash, name, now, now))
        conn.execute(
            "INSERT INTO onboarding_profiles (user_id, updated_at) VALUES (?, ?)",
            (user_id, now)
        )
        conn.commit()

        token = create_jwt(user_id, device_id, email=email)
        return {
            "user_id": user_id,
            "token": token,
            "new_user": True,
            "onboarding_complete": False,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Register-email error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        conn.close()


@router.post("/auth/login-email")
async def api_login_email(request: Request):
    """
    邮箱登录

    Request:
        {"email": "user@example.com", "password": "明文密码"}

    Response:
        {"token": "jwt...", "user_id": "uuid", "onboarding_complete": true/false}
    Errors: 401 (邮箱或密码错误)
    """
    body = await request.json()
    email = (body.get("email") or "").strip().lower()
    password = (body.get("password") or "")

    if not email or not password:
        raise HTTPException(status_code=400, detail="请输入邮箱和密码")

    conn = _get_db()
    try:
        user = conn.execute(
            "SELECT user_id, device_id, password_hash FROM users WHERE email = ? AND email_registered = 1",
            (email,)
        ).fetchone()

        if not user or not pwd_context.verify(password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="邮箱或密码错误")

        user_id = user["user_id"]
        now = datetime.now().isoformat()
        conn.execute(
            "UPDATE users SET last_active_at = ? WHERE user_id = ?",
            (now, user_id)
        )
        conn.commit()

        profile = conn.execute(
            "SELECT onboarding_complete FROM onboarding_profiles WHERE user_id = ?",
            (user_id,)
        ).fetchone()
        onboarding_complete = bool(profile and profile["onboarding_complete"])

        token = create_jwt(user_id, user["device_id"], email=email)
        return {
            "user_id": user_id,
            "token": token,
            "onboarding_complete": onboarding_complete,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Login-email error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        conn.close()


@router.get("/auth/verify")
async def api_verify_token(authorization: str = Header(...)):
    """
    验证 token 是否有效

    Response:
        {"valid": true, "user_id": "dev_xxxxxx"}
    """
    try:
        user_id = verify_user(authorization)
        return {"valid": True, "user_id": user_id}
    except HTTPException:
        return JSONResponse({"valid": False, "user_id": ""}, status_code=401)


@router.get("/user/onboarding-status")
async def api_onboarding_status(authorization: str = Header(...)):
    """查询用户是否完成问卷（APP 启动时调用）"""
    user_id = verify_user(authorization)

    conn = _get_db()
    try:
        profile = conn.execute(
            "SELECT onboarding_complete FROM onboarding_profiles WHERE user_id = ?",
            (user_id,)
        ).fetchone()
        onboarding_complete = bool(profile and profile["onboarding_complete"])
        return {"onboarding_complete": onboarding_complete}
    finally:
        conn.close()


# ============================================================
# Phase 2: 问卷 JSON 读取
# ============================================================

def _load_survey_json() -> dict:
    """加载 onboarding_survey.json，不存在则用内置模板"""
    if os.path.exists(ONBOARDING_JSON_PATH):
        with open(ONBOARDING_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    return {
        "version": "1.0",
        "questions": [
            {
                "id": "q_identity",
                "order": 1,
                "text": "你目前的身份是？",
                "type": "single_choice",
                "options": [
                    {"id": "student", "text": "在校学生", "next_id": "q_major"},
                    {"id": "worker", "text": "在职人员", "next_id": "q_field"},
                    {"id": "hobbyist", "text": "编程爱好者", "next_id": "q_interest"}
                ]
            },
            {
                "id": "q_major",
                "order": 2,
                "text": "你的专业是？",
                "type": "single_choice",
                "options": [
                    {"id": "cs", "text": "计算机/软件工程", "next_id": "q_cs_branch"},
                    {"id": "other", "text": "其他专业", "next_id": "q_interest"}
                ]
            },
            {
                "id": "q_field",
                "order": 2,
                "text": "你从事什么领域？",
                "type": "single_choice",
                "options": [
                    {"id": "it_dev", "text": "IT 开发", "next_id": "q_it_level"},
                    {"id": "it_other", "text": "IT 相关（运维/测试/产品）", "next_id": "q_interest"},
                    {"id": "non_it", "text": "非 IT，想转行", "next_id": "q_interest"}
                ]
            },
            {
                "id": "q_it_level",
                "order": 3,
                "text": "你的 IT 水平是？",
                "type": "single_choice",
                "options": [
                    {"id": "junior", "text": "初学者/Junior", "next_id": "q_interest"},
                    {"id": "mid", "text": "中级开发者", "next_id": "q_interest"},
                    {"id": "senior", "text": "高级/架构", "next_id": "q_interest"}
                ]
            },
            {
                "id": "q_interest",
                "order": 3,
                "text": "你对哪些领域感兴趣？（选 1-3 个）",
                "type": "multi_choice",
                "max_select": 3,
                "options": [
                    {"id": "cs", "text": "计算机科学", "next_id": "q_cs_branch"},
                    {"id": "physics", "text": "物理", "next_id": "q_physics_branch"},
                    {"id": "math", "text": "数学", "next_id": "q_math_branch"},
                    {"id": "other", "text": "其他领域", "next_id": "q_other_field"}
                ]
            },
            {
                "id": "q_cs_branch",
                "order": 4,
                "text": "计算机科学中你最想深入哪个方向？",
                "type": "multi_choice",
                "max_select": 2,
                "options": [
                    {"id": "cs_ai", "text": "人工智能", "next_id": "q_cs_ai_detail"},
                    {"id": "cs_web", "text": "Web 开发", "next_id": "q_cs_web_detail"},
                    {"id": "cs_backend", "text": "后端开发", "next_id": "q_cs_backend_detail"},
                    {"id": "cs_mobile", "text": "移动开发", "next_id": "q_cs_mobile_detail"},
                    {"id": "cs_game", "text": "游戏开发", "next_id": "q_cs_game_detail"},
                    {"id": "cs_algo", "text": "算法与数据结构", "next_id": "q_cs_level"},
                    {"id": "cs_security", "text": "网络安全", "next_id": "q_cs_level"},
                    {"id": "cs_data", "text": "数据科学", "next_id": "q_cs_level"},
                    {"id": "cs_unsure", "text": "我还不确定具体方向", "next_id": "q_cs_level"}
                ]
            },
            {
                "id": "q_cs_ai_detail",
                "order": 5,
                "text": "AI 里你最感兴趣的是？",
                "type": "multi_choice",
                "max_select": 2,
                "options": [
                    {"id": "cs_ai_ml", "text": "机器学习基础", "next_id": "q_cs_level"},
                    {"id": "cs_ai_dl", "text": "深度学习", "next_id": "q_cs_level"},
                    {"id": "cs_ai_nlp", "text": "自然语言处理 / 大语言模型", "next_id": "q_cs_level"},
                    {"id": "cs_ai_cv", "text": "计算机视觉", "next_id": "q_cs_level"},
                    {"id": "cs_ai_rl", "text": "强化学习", "next_id": "q_cs_level"},
                    {"id": "cs_ai_unsure", "text": "我不确定", "next_id": "q_cs_level"}
                ]
            },
            {
                "id": "q_cs_web_detail",
                "order": 5,
                "text": "Web 开发你更倾向哪个方向？",
                "type": "multi_choice",
                "max_select": 2,
                "options": [
                    {"id": "cs_web_fe", "text": "前端（React/Vue）", "next_id": "q_cs_level"},
                    {"id": "cs_web_be", "text": "后端（Node/Python/Go）", "next_id": "q_cs_level"},
                    {"id": "cs_web_full", "text": "全栈", "next_id": "q_cs_level"},
                    {"id": "cs_web_unsure", "text": "我不确定", "next_id": "q_cs_level"}
                ]
            },
            {
                "id": "q_cs_backend_detail",
                "order": 5,
                "text": "后端开发你熟悉哪个技术栈？",
                "type": "multi_choice",
                "max_select": 2,
                "options": [
                    {"id": "cs_backend_python", "text": "Python (Django/Flask/FastAPI)", "next_id": "q_cs_level"},
                    {"id": "cs_backend_java", "text": "Java (Spring)", "next_id": "q_cs_level"},
                    {"id": "cs_backend_go", "text": "Go", "next_id": "q_cs_level"},
                    {"id": "cs_backend_node", "text": "Node.js", "next_id": "q_cs_level"},
                    {"id": "cs_backend_unsure", "text": "我不确定", "next_id": "q_cs_level"}
                ]
            },
            {
                "id": "q_cs_mobile_detail",
                "order": 5,
                "text": "移动开发你倾向哪个平台？",
                "type": "multi_choice",
                "max_select": 2,
                "options": [
                    {"id": "cs_mobile_android", "text": "Android (Kotlin)", "next_id": "q_cs_level"},
                    {"id": "cs_mobile_ios", "text": "iOS (Swift)", "next_id": "q_cs_level"},
                    {"id": "cs_mobile_cross", "text": "跨平台（Flutter/React Native）", "next_id": "q_cs_level"},
                    {"id": "cs_mobile_unsure", "text": "我不确定", "next_id": "q_cs_level"}
                ]
            },
            {
                "id": "q_cs_game_detail",
                "order": 5,
                "text": "游戏开发你熟悉哪个引擎？",
                "type": "multi_choice",
                "max_select": 2,
                "options": [
                    {"id": "cs_game_unity", "text": "Unity (C#)", "next_id": "q_cs_level"},
                    {"id": "cs_game_unreal", "text": "Unreal Engine (C++)", "next_id": "q_cs_level"},
                    {"id": "cs_game_indie", "text": "独立游戏/轻量引擎", "next_id": "q_cs_level"},
                    {"id": "cs_game_unsure", "text": "我不确定", "next_id": "q_cs_level"}
                ]
            },
            {
                "id": "q_cs_level",
                "order": 99,
                "text": "在选中的领域里，你的实际水平是？",
                "type": "single_choice",
                "options": [
                    {"id": "level_beginner", "text": "零基础/刚入门", "next_id": "q_goal"},
                    {"id": "level_intermediate", "text": "有一定基础，能做简单项目", "next_id": "q_goal"},
                    {"id": "level_advanced", "text": "有经验，想深入进阶", "next_id": "q_goal"},
                    {"id": "level_unsure", "text": "不确定自己水平", "next_id": "q_goal"}
                ]
            },
            {
                "id": "q_physics_branch",
                "order": 4,
                "text": "物理中你最感兴趣的方向是？",
                "type": "multi_choice",
                "max_select": 2,
                "options": [
                    {"id": "physics_mech", "text": "力学", "next_id": "q_physics_level"},
                    {"id": "physics_em", "text": "电磁学", "next_id": "q_physics_level"},
                    {"id": "physics_quantum", "text": "量子物理", "next_id": "q_physics_level"},
                    {"id": "physics_thermo", "text": "热力学", "next_id": "q_physics_level"},
                    {"id": "physics_optics", "text": "光学", "next_id": "q_physics_level"},
                    {"id": "physics_rel", "text": "相对论", "next_id": "q_physics_level"},
                    {"id": "physics_unsure", "text": "我不确定", "next_id": "q_physics_level"}
                ]
            },
            {
                "id": "q_physics_level",
                "order": 99,
                "text": "在选中的物理领域里，你的实际水平是？",
                "type": "single_choice",
                "options": [
                    {"id": "level_beginner", "text": "零基础/刚入门", "next_id": "q_goal"},
                    {"id": "level_intermediate", "text": "学过基础，能做简单计算", "next_id": "q_goal"},
                    {"id": "level_advanced", "text": "有深入理解，想进阶", "next_id": "q_goal"},
                    {"id": "level_unsure", "text": "不确定自己水平", "next_id": "q_goal"}
                ]
            },
            {
                "id": "q_math_branch",
                "order": 4,
                "text": "数学中你最感兴趣的方向是？",
                "type": "multi_choice",
                "max_select": 2,
                "options": [
                    {"id": "math_calculus", "text": "微积分", "next_id": "q_math_level"},
                    {"id": "math_linalg", "text": "线性代数", "next_id": "q_math_level"},
                    {"id": "math_prob", "text": "概率统计", "next_id": "q_math_level"},
                    {"id": "math_discrete", "text": "离散数学", "next_id": "q_math_level"},
                    {"id": "math_de", "text": "微分方程", "next_id": "q_math_level"},
                    {"id": "math_abstract", "text": "抽象代数", "next_id": "q_math_level"},
                    {"id": "math_other", "text": "其他", "next_id": "q_math_level"},
                    {"id": "math_unsure", "text": "我不确定", "next_id": "q_math_level"}
                ]
            },
            {
                "id": "q_math_level",
                "order": 99,
                "text": "在选中的数学领域里，你的实际水平是？",
                "type": "single_choice",
                "options": [
                    {"id": "level_beginner", "text": "零基础/刚入门", "next_id": "q_goal"},
                    {"id": "level_intermediate", "text": "学过基础，能做练习题", "next_id": "q_goal"},
                    {"id": "level_advanced", "text": "有深入理解，想进阶", "next_id": "q_goal"},
                    {"id": "level_unsure", "text": "不确定自己水平", "next_id": "q_goal"}
                ]
            },
            {
                "id": "q_other_field",
                "order": 4,
                "text": "请描述你感兴趣的领域",
                "type": "single_choice",
                "options": [
                    {"id": "other_specified", "text": "（APP 提供自由输入框）", "next_id": "q_goal"}
                ]
            },
            {
                "id": "q_goal",
                "order": 100,
                "text": "你学习的主要目标是？",
                "type": "multi_choice",
                "max_select": 2,
                "options": [
                    {"id": "goal_career", "text": "求职/转行", "next_id": None},
                    {"id": "goal_project", "text": "完成具体项目", "next_id": None},
                    {"id": "goal_theory", "text": "理论深入理解", "next_id": None},
                    {"id": "goal_exam", "text": "考试/升学", "next_id": None},
                    {"id": "goal_hobby", "text": "纯粹兴趣", "next_id": None}
                ]
            }
        ]
    }


# ============================================================
# Phase 2: 问卷树构建
# ============================================================

def _build_question_tree() -> list:
    """构建完整问卷树（含追问分支逻辑）"""
    survey = _load_survey_json()
    questions = {q["id"]: q for q in survey["questions"]}

    def _build_from(q_id: str) -> dict:
        q = questions.get(q_id)
        if not q:
            return None

        node = {
            "id": q["id"],
            "order": q.get("order", 99),
            "text": q["text"],
            "type": q["type"],
            "options": []
        }
        if "max_select" in q:
            node["max_select"] = q["max_select"]

        for opt in q["options"]:
            opt_node = {
                "id": opt["id"],
                "text": opt["text"],
                "next_id": opt.get("next_id"),
            }
            if opt.get("next_id") and opt["next_id"] in questions:
                child_tree = _build_from(opt["next_id"])
                if child_tree:
                    opt_node["children"] = [child_tree]
            node["options"].append(opt_node)

        return node

    tree = _build_from("q_identity")
    return [tree] if tree else []


# ============================================================
# Phase 2: 答案处理
# ============================================================

# 目标 ID → readable name 映射
_GOAL_MAP = {
    "goal_career": "career",
    "goal_project": "project",
    "goal_theory": "theory",
    "goal_exam": "exam",
    "goal_hobby": "hobby",
}


def _process_answers(raw_answers: list) -> dict:
    """
    处理原始答案，生成用户人设。
    自动处理三种流程：
      1. student → cs  （q_interest 跳过）
      2. worker → it_dev → q_interest （q_interest 有回答）
      3. hobbyist → q_interest （q_interest 有回答）
    """
    result = {
        "identity": "",
        "identity_detail": "",
        "interests": [],
        "interests_detail": {},
        "skill_levels": {},
        "unsure_topics": [],
        "learning_goals": [],
    }

    answers_map = {}
    for entry in raw_answers:
        qid = entry.get("question_id", "")
        ans = entry.get("answer", [])
        answers_map[qid] = ans if isinstance(ans, list) else [ans]

    # 身份
    identity_ans = answers_map.get("q_identity", [])
    if identity_ans:
        result["identity"] = identity_ans[0]

    # 专业/领域
    if result["identity"] == "student":
        major_ans = answers_map.get("q_major", [])
        if major_ans:
            result["identity_detail"] = major_ans[0]
    elif result["identity"] == "worker":
        field_ans = answers_map.get("q_field", [])
        if field_ans:
            result["identity_detail"] = field_ans[0]

    # 兴趣领域（q_interest 有回答时）
    interest_ans = answers_map.get("q_interest", [])
    result["interests"] = interest_ans

    # 当 q_interest 未被回答时（student+cs 或 worker+it_dev 直接进入分支），
    # 从 identity_detail 推断 interests
    if not result["interests"] and result["identity_detail"]:
        result["interests"] = [result["identity_detail"]]

    # 各领域细分
    detail_map = {}
    for qid, ans in answers_map.items():
        if qid == "q_cs_branch":
            topic = "cs"
            detail_map[topic] = _map_cs_branch(ans, answers_map)
        elif qid == "q_physics_branch":
            topic = "physics"
            detail_map[topic] = _map_physics_branch(ans)
        elif qid == "q_math_branch":
            topic = "math"
            detail_map[topic] = _map_math_branch(ans)

        # unsure 标记
        if isinstance(ans, list):
            for a in ans:
                if "unsure" in a:
                    result["unsure_topics"].append(a)

    result["interests_detail"] = detail_map

    # 水平
    for qid in ["q_cs_level", "q_physics_level", "q_math_level"]:
        level_ans = answers_map.get(qid, [])
        if level_ans:
            if qid == "q_cs_level":
                for interest in detail_map.get("cs", {}).keys():
                    result["skill_levels"][interest] = _map_level(level_ans[0])
            elif qid == "q_physics_level":
                for interest in detail_map.get("physics", {}).keys():
                    result["skill_levels"][interest] = _map_level(level_ans[0])
            elif qid == "q_math_level":
                for interest in detail_map.get("math", {}).keys():
                    result["skill_levels"][interest] = _map_level(level_ans[0])

    # 目标（映射为 readable name）
    goal_ans = answers_map.get("q_goal", [])
    result["learning_goals"] = [
        _GOAL_MAP.get(g, g) for g in goal_ans if g in _GOAL_MAP
    ]

    return result


def _map_cs_branch(branches: list, all_answers: dict) -> dict:
    """将 CS 分支映射为 readable names"""
    mapping = {}
    for b in branches:
        if b == "cs_unsure":
            continue
        if b == "cs_ai":
            ai_answers = all_answers.get("q_cs_ai_detail", [])
            ai_mapped = []
            for a in ai_answers:
                ai_map = {
                    "cs_ai_ml": "machine_learning",
                    "cs_ai_dl": "deep_learning",
                    "cs_ai_nlp": "nlp",
                    "cs_ai_cv": "computer_vision",
                    "cs_ai_rl": "reinforcement_learning",
                }
                if a in ai_map:
                    ai_mapped.append(ai_map[a])
            mapping["artificial_intelligence"] = ai_mapped
        elif b == "cs_web":
            web_answers = all_answers.get("q_cs_web_detail", [])
            web_mapped = []
            for a in web_answers:
                web_map = {
                    "cs_web_fe": "web_frontend",
                    "cs_web_be": "web_backend",
                    "cs_web_full": "full_stack",
                }
                if a in web_map:
                    web_mapped.append(web_map[a])
            mapping["web_development"] = web_mapped
        elif b == "cs_backend":
            be_answers = all_answers.get("q_cs_backend_detail", [])
            be_mapped = []
            for a in be_answers:
                be_map = {
                    "cs_backend_python": "python_backend",
                    "cs_backend_java": "java_backend",
                    "cs_backend_go": "go_backend",
                    "cs_backend_node": "node_backend",
                }
                if a in be_map:
                    be_mapped.append(be_map[a])
            mapping["backend_development"] = be_mapped
        elif b == "cs_mobile":
            mob_answers = all_answers.get("q_cs_mobile_detail", [])
            mob_mapped = []
            for a in mob_answers:
                mob_map = {
                    "cs_mobile_android": "android",
                    "cs_mobile_ios": "ios",
                    "cs_mobile_cross": "cross_platform",
                }
                if a in mob_map:
                    mob_mapped.append(mob_map[a])
            mapping["mobile_development"] = mob_mapped
        elif b == "cs_game":
            game_answers = all_answers.get("q_cs_game_detail", [])
            game_mapped = []
            for a in game_answers:
                game_map = {
                    "cs_game_unity": "unity",
                    "cs_game_unreal": "unreal",
                    "cs_game_indie": "indie_game",
                }
                if a in game_map:
                    game_mapped.append(game_map[a])
            mapping["game_development"] = game_mapped
        elif b == "cs_algo":
            mapping["algorithms_data_structures"] = []
        elif b == "cs_security":
            mapping["cybersecurity"] = []
        elif b == "cs_data":
            mapping["data_science"] = []
    return mapping


def _map_physics_branch(branches: list) -> dict:
    """将物理分支映射为 readable names"""
    mapping = {}
    phys_map = {
        "physics_mech": "mechanics",
        "physics_em": "electromagnetism",
        "physics_quantum": "quantum_physics",
        "physics_thermo": "thermodynamics",
        "physics_optics": "optics",
        "physics_rel": "relativity",
    }
    for b in branches:
        if b in phys_map:
            mapping[phys_map[b]] = []
    return mapping


def _map_math_branch(branches: list) -> dict:
    """将数学分支映射为 readable names"""
    mapping = {}
    math_map = {
        "math_calculus": "calculus",
        "math_linalg": "linear_algebra",
        "math_prob": "probability_statistics",
        "math_discrete": "discrete_math",
        "math_de": "differential_equations",
        "math_abstract": "abstract_algebra",
        "math_other": "other_math",
    }
    for b in branches:
        if b in math_map:
            mapping[math_map[b]] = []
    return mapping


def _map_level(level_id: str) -> str:
    """映射水平级别"""
    level_map = {
        "level_beginner": "beginner",
        "level_intermediate": "intermediate",
        "level_advanced": "advanced",
        "level_unsure": "unsure",
    }
    return level_map.get(level_id, "beginner")


# ============================================================
# Phase 2 & 3: Onboarding API
# ============================================================


@router.get("/onboarding/tree")
async def api_onboarding_tree(authorization: str = Header(...)):
    """获取完整问卷树"""
    verify_user(authorization)

    survey = _load_survey_json()
    tree = _build_question_tree()
    return {
        "version": survey["version"],
        "tree": tree,
    }


@router.post("/onboarding/complete")
async def api_onboarding_complete(
    request: Request,
    authorization: str = Header(...),
):
    """提交问卷答案，生成用户人设"""
    user_id = verify_user(authorization)

    body = await request.json()
    answers = body.get("answers", [])
    if not answers:
        raise HTTPException(status_code=400, detail="answers is required")

    processed = _process_answers(answers)

    now = datetime.now().isoformat()
    conn = _get_db()
    try:
        existing_user = conn.execute(
            "SELECT user_id FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        if not existing_user and user_id != "admin":
            raise HTTPException(status_code=404, detail="User not found")

        conn.execute("""
            INSERT INTO onboarding_profiles (
                user_id, identity, identity_detail,
                interests, interests_detail, skill_levels,
                unsure_topics, learning_goals,
                onboarding_complete, raw_answers,
                onboarding_version, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, '1.0', ?)
            ON CONFLICT(user_id) DO UPDATE SET
                identity=excluded.identity,
                identity_detail=excluded.identity_detail,
                interests=excluded.interests,
                interests_detail=excluded.interests_detail,
                skill_levels=excluded.skill_levels,
                unsure_topics=excluded.unsure_topics,
                learning_goals=excluded.learning_goals,
                onboarding_complete=1,
                raw_answers=excluded.raw_answers,
                updated_at=excluded.updated_at
        """, (
            user_id,
            processed["identity"],
            processed["identity_detail"],
            json.dumps(processed["interests"], ensure_ascii=False),
            json.dumps(processed["interests_detail"], ensure_ascii=False),
            json.dumps(processed["skill_levels"], ensure_ascii=False),
            json.dumps(processed["unsure_topics"], ensure_ascii=False),
            json.dumps(processed["learning_goals"], ensure_ascii=False),
            json.dumps(answers, ensure_ascii=False),
            now,
        ))
        conn.commit()

        logger.info("User %s 完成 onboarding", user_id)

        return {
            "user_id": user_id,
            "profile": processed,
            "status": "ok",
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Onboarding complete error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        conn.close()


# ============================================================
# Phase 3: Profile API
# ============================================================


@router.get("/user/onboarding-status")
async def api_onboarding_status(authorization: str = Header(...)):
    """查询用户是否已完成 onboarding"""
    user_id = verify_user(authorization)

    conn = _get_db()
    try:
        profile = conn.execute(
            "SELECT onboarding_complete FROM onboarding_profiles WHERE user_id = ?",
            (user_id,)
        ).fetchone()

        if not profile:
            if user_id == "admin":
                return {"onboarding_complete": True}
            raise HTTPException(status_code=404, detail="Profile not found")

        return {"onboarding_complete": bool(profile["onboarding_complete"])}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Onboarding status error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        conn.close()


@router.get("/user/profile")
async def api_get_profile(authorization: str = Header(...)):
    """获取用户人设（含邮箱注册信息）"""
    user_id = verify_user(authorization)

    conn = _get_db()
    try:
        row = conn.execute(
            """SELECT u.name, u.email, u.avatar_url, u.registered_at,
                      op.identity, op.identity_detail, op.interests,
                      op.interests_detail, op.skill_levels, op.unsure_topics,
                      op.learning_goals, op.onboarding_complete,
                      op.onboarding_version, op.updated_at
               FROM users u
               LEFT JOIN onboarding_profiles op ON op.user_id = u.user_id
               WHERE u.user_id = ?""",
            (user_id,)
        ).fetchone()

        if not row:
            if user_id == "admin":
                return {
                    "user_id": "admin",
                    "profile": {
                        "name": "管理员",
                        "email": "",
                        "avatar_url": "",
                        "created_at": "",
                        "identity": "",
                        "identity_detail": "",
                        "interests": [],
                        "interests_detail": {},
                        "skill_levels": {},
                        "unsure_topics": [],
                        "learning_goals": [],
                        "onboarding_complete": False,
                        "onboarding_version": "",
                        "updated_at": "",
                    }
                }
            raise HTTPException(status_code=404, detail="User not found")

        return {
            "user_id": user_id,
            "profile": {
                "name": row["name"] or "",
                "email": row["email"] or "",
                "avatar_url": row["avatar_url"] or "",
                "created_at": row["registered_at"] or "",
                "identity": row["identity"] or "",
                "identity_detail": row["identity_detail"] or "",
                "interests": json.loads(row["interests"] or "[]"),
                "interests_detail": json.loads(row["interests_detail"] or "{}"),
                "skill_levels": json.loads(row["skill_levels"] or "{}"),
                "unsure_topics": json.loads(row["unsure_topics"] or "[]"),
                "learning_goals": json.loads(row["learning_goals"] or "[]"),
                "onboarding_complete": bool(row["onboarding_complete"]),
                "onboarding_version": row["onboarding_version"] or "",
                "updated_at": row["updated_at"] or "",
            }
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Get profile error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        conn.close()


@router.put("/user/profile")
async def api_update_profile(
    request: Request,
    authorization: str = Header(...),
):
    """
    更新用户资料。支持字段：name, phone, unsure_topics
    """
    user_id = verify_user(authorization)

    body = await request.json()
    name = body.get("name")
    phone = body.get("phone")
    unsure_topics = body.get("unsure_topics")

    now = datetime.now().isoformat()
    conn = _get_db()
    try:
        # Update users table for name and phone
        if name is not None or phone is not None:
            # Check if user exists; if not, INSERT instead of UPDATE
            exists = conn.execute(
                "SELECT 1 FROM users WHERE user_id = ?", (user_id,)
            ).fetchone()
            if exists:
                updates = []
                params = []
                if name is not None:
                    updates.append("name = ?")
                    params.append(name)
                if phone is not None:
                    updates.append("phone = ?")
                    params.append(phone)
                if updates:
                    params.extend([now, user_id])
                    conn.execute(
                        f"UPDATE users SET {', '.join(updates)}, last_active_at = ? WHERE user_id = ?",
                        params
                    )
            else:
                conn.execute(
                    "INSERT INTO users (user_id, name, phone, registered_at, last_active_at) VALUES (?, ?, ?, ?, ?)",
                    (user_id, name or "", phone or "", now, now)
                )
            conn.commit()

        # Update unsure_topics if provided
        if unsure_topics is not None:
            existing = conn.execute(
                "SELECT * FROM onboarding_profiles WHERE user_id = ?",
                (user_id,)
            ).fetchone()

            if existing:
                current_unsure = json.loads(existing["unsure_topics"] or "[]")
                merged = list(set(list(unsure_topics) + current_unsure))
                conn.execute(
                    "UPDATE onboarding_profiles SET unsure_topics = ?, updated_at = ? WHERE user_id = ?",
                    (json.dumps(merged, ensure_ascii=False), now, user_id)
                )
                conn.commit()
                logger.info("User %s unsure_topics updated: %s", user_id, merged)

        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Update profile error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        conn.close()


# ============================================================
# App 版本更新
# ============================================================

@router.get("/app/version")
async def api_app_version():
    """返回最新版本信息，供 APP 检查更新（无需认证）"""
    return {
        "version": 2,
        "version_name": "1.1.0",
        "download_url": "http://8.162.10.45/app-debug.apk",
        "changelog": "修复了退出登录后无法跳转的问题；优化了问答选项存储逻辑",
        "force_update": False,
    }


# ============================================================
# APP 版本检查（无需登录）
# ============================================================

@router.get("/app/version")
async def api_app_version():
    """
    返回最新 APP 版本信息，供客户端检查更新。
    此接口不需要登录 token。

    Response:
        {
            "version": 2,
            "version_name": "1.1.0",
            "download_url": "https://your-cdn.com/app-debug.apk",
            "changelog": "修复了退出登录后无法跳转的问题",
            "force_update": false
        }
    """
    return {
        "version": 2,
        "version_name": "1.1.0",
        "download_url": "https://your-cdn.com/app-debug.apk",
        "changelog": "修复了退出登录后无法跳转的问题",
        "force_update": False,
    }


# ============================================================
# 初始化
# ============================================================

init_onboarding_db()