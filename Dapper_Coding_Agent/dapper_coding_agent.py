"""
Dapper Coding AI Agent
每天早上 8:00 生成个性化问候语并通过飞书推送。

依赖：
- requests
- APScheduler
"""

import json
import hashlib
import html
import logging
import os
import base64
import re
import secrets
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from urllib.parse import urlparse

import requests
from apscheduler.schedulers.blocking import BlockingScheduler
from fastapi import BackgroundTasks, FastAPI, Request, Query
from fastapi.responses import HTMLResponse, Response, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import xml.etree.ElementTree as ET
from urllib.parse import unquote
import base64
import hashlib
import xml.etree.ElementTree as ET
from urllib.parse import unquote
import base64
import hashlib


def env_bool(name: str, default: bool) -> bool:
    """读取布尔环境变量。"""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def resolve_env_file(env_file: str = ".env") -> str:
    """解析 .env 路径，优先环境变量 DAPPER_ENV_FILE，其次脚本同级目录。"""
    override = os.getenv("DAPPER_ENV_FILE", "").strip()
    if override:
        return os.path.abspath(override)
    if os.path.isabs(env_file):
        return env_file
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, env_file)


def load_local_env(env_file: str = ".env") -> Optional[str]:
    """加载 .env（仅填充当前进程中尚未存在的变量），返回实际加载路径。"""
    resolved = resolve_env_file(env_file)
    if not os.path.exists(resolved):
        return None

    try:
        with open(resolved, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
    except Exception as exc:
        logging.warning("读取 .env 失败，将继续使用系统环境变量。错误：%s", exc)
        return None

    return resolved


# 启动时加载项目根目录 .env（如果存在）
LOADED_ENV_PATH = load_local_env()


# =============================
# 配置模块（可改为环境变量）
# =============================

LLM_API_KEY = os.getenv("LLM_API_KEY", "")
# OpenAI 兼容地址，默认使用 MiniMax 兼容地址；如使用第三方可替换为其兼容地址
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.minimax.chat/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "minimax-m2.7")

# 和风天气 / 旧版天气兜底配置
HEWEATHER_API_KEY = os.getenv("HEWEATHER_API_KEY", os.getenv("WEATHER_API_KEY", ""))
WEATHER_LOCATION = os.getenv("WEATHER_LOCATION", os.getenv("WEATHER_CITY", "")).strip()
WEATHER_LAT = os.getenv("WEATHER_LAT", "31.2304").strip()
WEATHER_LON = os.getenv("WEATHER_LON", "121.4737").strip()

EXTERNAL_TIMEOUT = float(os.getenv("EXTERNAL_TIMEOUT", "4"))
NEWS_ENABLED = env_bool("NEWS_ENABLED", True)
WEATHER_ENABLED = env_bool("WEATHER_ENABLED", True)
QWEATHER_ENABLED = env_bool("QWEATHER_ENABLED", True)
DB_PATH = resolve_env_file("dapper_memory.db")
SCOUT_ENABLED = env_bool("SCOUT_ENABLED", True)
DIGEST_ENABLED = env_bool("DIGEST_ENABLED", True)
SCOUT_DAILY_LIMIT = max(1, min(int(os.getenv("SCOUT_DAILY_LIMIT", "5") or "5"), 20))


# 企业微信应用配置
WEIXIN_CORP_ID = os.getenv("WEIXIN_CORP_ID", "")
WEIXIN_AGENT_ID = os.getenv("WEIXIN_AGENT_ID", "")
WEIXIN_CORP_SECRET = os.getenv("WEIXIN_CORP_SECRET", "")
WEIXIN_CALLBACK_TOKEN = os.getenv("WEIXIN_CALLBACK_TOKEN", "")
WEIXIN_CALLBACK_AES_KEY = os.getenv("WEIXIN_CALLBACK_AES_KEY", "")
WEIXIN_WEBHOOK_URL = os.getenv("WEIXIN_WEBHOOK_URL", "")
DIGEST_ENABLED = env_bool("DIGEST_ENABLED", True)
WEB_ENABLED = env_bool("WEB_ENABLED", True)
WEB_ADMIN_PASSWORD = os.getenv("WEB_ADMIN_PASSWORD", "")

# 设为 true 时不请求真实 LLM，方便本地联调
LLM_SIMULATE = os.getenv("LLM_SIMULATE", "false").lower() == "true"
# 设为 true 时不请求飞书鉴权/消息接口，方便本地联调

# 日志等级：DEBUG / INFO / WARNING / ERROR
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# === Feishu stubs (deprecated) - kept to avoid NameError in remaining dead code ===
FEISHU_APP_ID = ""
FEISHU_APP_SECRET = ""
FEISHU_VERIFICATION_TOKEN = ""
FEISHU_VERIFY_ENABLED = False
FEISHU_SIMULATE = False


# 用户画像配置：可通过 USER_PROFILES_JSON 覆盖
# 例子：
# USER_PROFILES_JSON='[{"open_id":"ou_xxx","feature":"喜欢晨跑和咖啡"}]'
DEFAULT_USER_PROFILES: List[Dict[str, str]] = [
    {
        "open_id": "ou_example_001",
        "feature": "早起型产品经理，喜欢晨跑和黑咖啡，关注效率工具",
    },
    {
        "open_id": "ou_example_002",
        "feature": "后端工程师，重视代码质量，最近在学习大模型应用开发",
    },
]


def get_requests_proxies() -> Optional[Dict[str, str]]:
    """读取代理设置，便于在受限网络环境中访问外部 API。"""
    if not env_bool("REQUESTS_PROXY_ENABLED", True):
        return None

    https_proxy = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy") or os.getenv("ALL_PROXY")
    http_proxy = os.getenv("HTTP_PROXY") or os.getenv("http_proxy") or os.getenv("ALL_PROXY")
    proxies: Dict[str, str] = {}
    if https_proxy:
        proxies["https"] = https_proxy
    if http_proxy:
        proxies["http"] = http_proxy
    return proxies or None


REQUEST_PROXIES = get_requests_proxies()


def build_request_kwargs(timeout: float) -> Dict[str, object]:
    """统一构建 requests 参数。"""
    kwargs: Dict[str, object] = {"timeout": timeout}
    if REQUEST_PROXIES:
        kwargs["proxies"] = REQUEST_PROXIES
    return kwargs


def endpoint_host(url: str) -> str:
    """提取日志展示用 host。"""
    return urlparse(url).netloc or url


def init_memory_db() -> None:
    """初始化长期记忆数据库与表结构。"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            # noinspection SqlDialectInspection
            conn.execute(
                # language=SQLite
                """
                CREATE TABLE IF NOT EXISTS greetings_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    send_date TEXT NOT NULL,
                    open_id TEXT NOT NULL,
                    message TEXT NOT NULL
                )
                """
            )
            # noinspection SqlDialectInspection
            conn.execute(
                # language=SQLite
                """
                """
            )
            # noinspection SqlDialectInspection
            conn.execute(
                # language=SQLite
                """
                """
            )
            # noinspection SqlDialectInspection
            conn.execute(
                # language=SQLite
                """
                CREATE TABLE IF NOT EXISTS user_conversations (
                    user_id TEXT PRIMARY KEY,
                    state TEXT NOT NULL DEFAULT 'INIT',
                    direction TEXT,
                    current_day INTEGER DEFAULT 1,
                    daily_push_time TEXT DEFAULT '20:00',
                    daily_learning_minutes INTEGER DEFAULT 60,
                    conversation_style TEXT DEFAULT 'friendly',
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()
    except Exception as exc:
        logging.error("初始化记忆数据库失败(path=%s): %s", DB_PATH, exc)


def get_recent_memory(open_id: str, days: int = 3) -> str:
    """读取用户最近几天的问候历史，作为长期记忆上下文。"""
    if not open_id:
        return "无历史记录"

    try:
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        with sqlite3.connect(DB_PATH) as conn:
            # noinspection SqlDialectInspection
            cursor = conn.execute(
                # language=SQLite
                """
                SELECT send_date, message
                FROM greetings_history
                WHERE open_id = ? AND send_date >= ?
                ORDER BY send_date DESC, id DESC
                """,
                (open_id, cutoff),
            )
            rows = cursor.fetchall()

        if not rows:
            return "无历史记录"

        history_lines = [f"{send_date}: {message}" for send_date, message in rows]
        return "\n".join(history_lines)
    except Exception as exc:
        logging.warning("读取长期记忆失败(open_id=%s): %s", open_id, exc)
        return "无历史记录"


def save_to_memory(open_id: str, message: str) -> None:
    """写入当天成功发送的问候语到长期记忆。"""
    if not open_id or not message:
        return

    try:
        send_date = datetime.now().strftime("%Y-%m-%d")
        with sqlite3.connect(DB_PATH) as conn:
            # noinspection SqlDialectInspection
            conn.execute(
                # language=SQLite
                """
                INSERT INTO greetings_history(send_date, open_id, message)
                VALUES(?, ?, ?)
                """,
                (send_date, open_id, message),
            )
            conn.commit()
    except Exception as exc:
        logging.error("写入长期记忆失败(open_id=%s): %s", open_id, exc)










def load_user_profiles() -> List[Dict[str, str]]:
    """加载用户画像配置，优先读取环境变量。"""
    raw = os.getenv("USER_PROFILES_JSON", "").strip()
    if not raw:
        return DEFAULT_USER_PROFILES

    try:
        profiles = json.loads(raw)
        if not isinstance(profiles, list):
            raise ValueError("USER_PROFILES_JSON 必须是列表 JSON")
        return profiles
    except Exception as exc:
        logging.warning("USER_PROFILES_JSON 解析失败，回退默认画像。错误：%s", exc)
        return DEFAULT_USER_PROFILES


def sanitize_message_text(text: str, fallback: str = "收到", limit: int = 3000) -> str:
    """清洗模型输出，去掉思维链、控制字符和多余空白。解除了长度封印，聊天可长篇大论。"""
    cleaned = re.sub(r"<think>.*?</think>", "", text or "", flags=re.S | re.I)
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", cleaned)
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = re.sub(r"[\t ]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    cleaned = cleaned[:limit].strip()
    return cleaned or fallback


def compact_greeting_text(text: str, limit: int = 120) -> str:
    """专门用于早安问候的压缩，依然保持短小精悍。"""
    cleaned = sanitize_message_text(text, limit=limit)
    cleaned = re.sub(r"[【\[]?客观环境数据[】\]]?[:：].*", "", cleaned, flags=re.S)
    cleaned = re.sub(r"[【\[]?目标用户画像[】\]]?[:：].*", "", cleaned, flags=re.S)
    cleaned = re.sub(r"[【\[]?任务指令[】\]]?[:：].*", "", cleaned, flags=re.S)
    cleaned = re.sub(r"[【\[]?严格约束[】\]]?[:：].*", "", cleaned, flags=re.S)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) > limit:
        cleaned = cleaned[:limit].rstrip("，,。.!！?？;；、")
    return cleaned or "早上好呀！愿你今天顺利，灵感满满。"


def get_current_time_text() -> str:
    """返回适合写入 prompt 的本地时间描述。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def get_weather_info() -> str:
    """获取天气信息，并强制打上城市标签防失忆。"""
    real_weather = get_real_weather()
    city_name = os.getenv("WEATHER_CITY", "南昌")
    return f"【{city_name}】{real_weather}" if real_weather else "天气暂不可用"


def get_daily_news() -> str:
    """获取行业资讯，优先走公共热榜接口，失败时回退到环境变量兜底。"""
    real_news = get_real_news()
    return real_news or "今日资讯暂不可用"


def get_real_news() -> str:
    """使用对云服务器极其稳定的 Hacker News API"""
    if not NEWS_ENABLED:
        legacy = os.getenv("DAILY_NEWS", "").strip()
        return legacy or "科技资讯已关闭"

    # Hacker News 官方开源的高可用搜索接口
    url = "https://hn.algolia.com/api/v1/search?tags=front_page"

    try:
        resp = requests.get(url, **build_request_kwargs(EXTERNAL_TIMEOUT))
        resp.raise_for_status()
        data = resp.json()

        hits = data.get("hits", [])
        if hits:
            # 提取排名第一的帖子标题
            title = (hits[0].get("title") or hits[0].get("story_title") or "未知标题").strip()
            return f"Hacker News 今日榜首热议：{title}"
    except Exception as exc:
        logging.warning("Hacker News 请求失败: %s", exc)

    legacy = os.getenv("DAILY_NEWS", "").strip()
    return legacy or "科技资讯暂不可用"


def get_real_weather() -> str:
    """优先和风天气，失败时回退 Open-Meteo。"""
    if not WEATHER_ENABLED:
        legacy = os.getenv("WEATHER_INFO", "").strip()
        return legacy or "天气功能已关闭"

    url = "https://pr4nmumupd.re.qweatherapi.com/v7/weather/now"
    params = {
        "location": WEATHER_LOCATION,
        "key": HEWEATHER_API_KEY,
        "lang": "zh",
    }

    if QWEATHER_ENABLED:
        try:
            if not HEWEATHER_API_KEY or not WEATHER_LOCATION:
                raise RuntimeError("未配置和风天气参数")

            resp = requests.get(url, params=params, **build_request_kwargs(EXTERNAL_TIMEOUT))
            resp.raise_for_status()
            data = resp.json()

            if str(data.get("code")) != "200":
                raise RuntimeError(f"和风天气接口返回异常: {data}")

            now_data = data.get("now", {})
            text = now_data.get("text", "天气未知")
            temp = now_data.get("temp", "-")
            feels_like = now_data.get("feelsLike", "-")
            wind_dir = now_data.get("windDir", "")
            wind_scale = now_data.get("windScale", "")

            parts = [f"{text}，气温 {temp}℃，体感 {feels_like}℃"]
            if wind_dir or wind_scale:
                parts.append(f"{wind_dir}{wind_scale}级".strip())
            return "，".join(parts)

        except Exception as exc:
            logging.warning("和风天气请求失败(host=%s)，将尝试 Open-Meteo: %s", endpoint_host(url), exc)
    else:
        logging.info("和风天气源已关闭(QWEATHER_ENABLED=false)，直接回退 Open-Meteo")

    open_meteo_url = "https://api.open-meteo.com/v1/forecast"
    try:
        om_params = {
            "latitude": WEATHER_LAT,
            "longitude": WEATHER_LON,
            "current": "temperature_2m,apparent_temperature,weather_code,wind_speed_10m",
            "timezone": "Asia/Shanghai",
        }
        resp = requests.get(open_meteo_url, params=om_params, **build_request_kwargs(EXTERNAL_TIMEOUT))
        resp.raise_for_status()
        data = resp.json()
        current = data.get("current", {})

        code = int(current.get("weather_code", -1)) if current.get("weather_code") is not None else -1
        weather_map = {
            0: "晴朗",
            1: "基本晴",
            2: "局部多云",
            3: "阴天",
            45: "雾",
            48: "雾凇",
            51: "小毛雨",
            61: "小雨",
            63: "中雨",
            65: "大雨",
            71: "小雪",
            73: "中雪",
            75: "大雪",
            80: "阵雨",
            95: "雷雨",
        }
        text = weather_map.get(code, f"天气代码{code}")
        temp = current.get("temperature_2m", "-")
        feels_like = current.get("apparent_temperature", "-")
        wind = current.get("wind_speed_10m", "-")
        return f"{text}，气温 {temp}℃，体感 {feels_like}℃，风速 {wind}km/h"
    except Exception as exc:
        logging.error("Open-Meteo 请求异常(host=%s): %s", endpoint_host(open_meteo_url), exc)

    legacy = os.getenv("WEATHER_INFO", "").strip()
    return legacy or "天气暂不可用"


def fetch_external_context() -> dict:
    """获取外部环境数据，作为 LLM 的感知上下文。"""
    now_str = datetime.now().strftime("%Y年%m月%d日 %H:%M")

    # 注入真实的天气数据
    real_weather = get_real_weather()

    # 注入真实的科技新闻数据！
    real_news = get_real_news()

    return {
        "time": now_str,
        "weather": real_weather,
        "news": real_news,
    }


def run_health_check() -> int:
    """执行配置与依赖预检，返回进程退出码（0=通过，1=失败）。"""
    logging.info("开始执行健康检查")

    try:
        validate_config()
        logging.info("配置检查通过")
    except Exception as exc:
        logging.error("配置检查失败: %s", exc)
        return 1

    # 外部上下文预检：即使降级到兜底文案也会给出可读日志
    context = fetch_external_context()
    logging.info("上下文检查: time=%s, weather=%s, news=%s", context.get("time"), context.get("weather"), context.get("news"))

    # LLM 预检：在模拟模式仅检查函数可用性，在真实模式执行一次轻量生成
    try:
        demo = generate_greeting(
            feature_desc="健康检查用户，关注自动化与后端稳定性",
            current_time=context.get("time"),
            weather_info=context.get("weather"),
            daily_news=context.get("news"),
        )
        logging.info("LLM 检查通过: greeting=%s", demo)
    except Exception as exc:
        logging.error("LLM 检查失败: %s", exc)
        return 1

    # Learning Scout 预检：检查订阅配置、抓取能力与 trafilatura 可用性
    if SCOUT_ENABLED:
        try:
            from learning_scout import run_learning_scout_healthcheck

            scout_ok, scout_msg = run_learning_scout_healthcheck()
            if scout_ok:
                logging.info("Learning Scout 检查通过: %s", scout_msg)
            else:
                logging.warning("Learning Scout 检查未通过: %s", scout_msg)
        except Exception as exc:
            logging.warning("Learning Scout 检查异常: %s", exc)
    else:
        logging.info("Learning Scout 检查跳过（SCOUT_ENABLED=false）")


    return 0


def build_greeting_prompt(
    feature_desc: str,
    current_time: str,
    weather_info: str,
    daily_news: str,
    recent_memory: str,
) -> str:
    """构建用于 LLM 的动态问候提示词。"""
    return (
        f"【客观环境数据】\n"
        f"当前时间：{current_time}\n"
        f"当地天气：{weather_info}\n"
        f"行业资讯：{daily_news}\n\n"
        f"【目标用户画像】\n"
        f"特征描述：{feature_desc}\n\n"
        f"【你的长期记忆】\n"
        f"{recent_memory}\n\n"
        f"【任务指令】\n"
        f"请结合上述[客观环境]和[用户画像]，为该用户生成今天的专属早安问候。\n\n"
        f"【严格约束】\n"
        f"绝对不能与【你的长期记忆】中的句式、切入点或主体立意重复！必须找一个新的切入点！\n"
        f"如果天气有雨雪降温，必须巧妙地给出穿衣或出行建议。\n"
        f"尝试将[行业资讯]与用户的[特征描述]结合。例如：如果用户在搞计算机视觉或 OpenCV，可以顺带提一句最新的 AI 视觉新闻；如果用户在弄 Docker 部署，可以祝他今天服务器不报 OOM。\n"
        f"语气自然、口语化，像一个真诚的极客老友。\n"
        f"严禁啰嗦，总字数控制在 80 字以内！不要输出多余的解释！"
    )


def validate_config() -> None:
    """启动前校验关键配置，避免运行时才暴露环境变量问题。"""
    missing = []


    if not LLM_SIMULATE:
        if not LLM_API_KEY:
            missing.append("LLM_API_KEY")

    if not LLM_BASE_URL:
        missing.append("LLM_BASE_URL")
    if not LLM_MODEL:
        missing.append("LLM_MODEL")

    if missing:
        raise ValueError(f"缺少必要环境变量: {', '.join(missing)}")


# =============================
# 飞书鉴权模块
# =============================
def get_tenant_access_token(app_id: str, app_secret: str) -> str:
    """获取飞书 tenant_access_token。"""
    if FEISHU_SIMULATE:
        return "mock_tenant_access_token"

    if not app_id or not app_secret:
        raise ValueError("缺少 FEISHU_APP_ID 或 FEISHU_APP_SECRET")

    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {"app_id": app_id, "app_secret": app_secret}

    resp = requests.post(url, json=payload, **build_request_kwargs(15))
    resp.raise_for_status()
    data = resp.json()

    if data.get("code") != 0:
        raise RuntimeError(f"飞书鉴权失败: {data}")

    token = data.get("tenant_access_token")
    if not token:
        raise RuntimeError(f"飞书鉴权成功但未返回 token: {data}")

    return token


# =============================
# LLM 大脑模块
# =============================
def generate_greeting(
    feature_desc: str,
    current_time: Optional[str] = None,
    weather_info: Optional[str] = None,
    daily_news: Optional[str] = None,
    recent_memory: Optional[str] = None,
) -> str:
    """根据用户特征生成问候语（OpenAI 兼容接口格式）。"""
    current_time = current_time or get_current_time_text()
    weather_info = weather_info or get_weather_info()
    daily_news = daily_news or get_daily_news()
    recent_memory = recent_memory or "无历史记录"

    # 模拟模式：避免开发调试阶段频繁调用外部 API
    if LLM_SIMULATE:
        return compact_greeting_text(
            f"早上好！现在是 {current_time.split()[-1]}，{weather_info}，愿你今天灵感满满、工作顺利。"
        )

    if not LLM_API_KEY:
        raise ValueError("缺少 LLM_API_KEY，或将 LLM_SIMULATE=true 用于本地模拟")

    url = f"{LLM_BASE_URL.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }

    system_prompt = (
        "你是一个贴心且极具专业素养的 AI 助理，代号 'Dapper Coding'。"
        "你擅长观察外部环境，并结合用户的个人特征，写出既有温度又聪明的早安问候。"
    )
    prompt = build_greeting_prompt(
        feature_desc=feature_desc,
        current_time=current_time,
        weather_info=weather_info,
        daily_news=daily_news,
        recent_memory=recent_memory,
    )

    body = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.8,
        "max_tokens": 2048,
    }

    resp = requests.post(url, headers=headers, json=body, **build_request_kwargs(30))
    resp.raise_for_status()
    data = resp.json()

    try:
        raw_content = data["choices"][0]["message"]["content"]
        return compact_greeting_text(raw_content)
    except Exception as exc:
        raise RuntimeError(f"LLM 返回格式异常: {data}") from exc


def generate_chat_reply(user_text: str, recent_memory: str) -> str:
    """根据用户消息、长期记忆和当前环境生成聊天回复。"""
    user_text = (user_text or "").strip()
    recent_memory = recent_memory or "无历史记录"

    if not user_text:
        return "我在，继续说。"

    if LLM_SIMULATE:
        return sanitize_message_text(f"收到你的消息了：{user_text}。我先帮你整理一下思路。", fallback="我在，继续说。")

    if not LLM_API_KEY:
        raise ValueError("缺少 LLM_API_KEY，或将 LLM_SIMULATE=true 用于本地模拟")

    url = f"{LLM_BASE_URL.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }

    # 在聊天时也注入最新外部环境数据
    ext_context = fetch_external_context()
    current_time = ext_context["time"]
    weather_info = ext_context["weather"]
    daily_news = ext_context["news"]

    system_prompt = (
        "你是一个贴心且极具专业素养的 AI 助理，代号 'Dapper Coding'。"
        "你擅长观察上下文，并结合用户的长期记忆，给出直接、友好、极客风格的回答。"
    )

    prompt = (
        f"【客观环境数据】\n"
        f"当前时间：{current_time}\n"
        f"当地天气：{weather_info}\n"
        f"行业资讯：{daily_news}\n\n"
        f"【你的长期记忆】\n"
        f"{recent_memory}\n\n"
        f"【用户消息】\n"
        f"{user_text}\n\n"
        f"【任务指令】\n"
        f"请直接回答用户消息，语气自然、友好、像一个真诚的极客老友。"
        f"如果用户问及当前时间、天气或新闻，请直接使用【客观环境数据】中的信息来回答，不要说你无法获取。"
        f"优先结合【你的长期记忆】给出有连续性的回应。"
        f"不要输出分析过程，不要啰嗦，不要输出多余解释。"
    )

    body = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 2048,
    }

    resp = requests.post(url, headers=headers, json=body, **build_request_kwargs(30))
    resp.raise_for_status()
    data = resp.json()

    try:
        raw_content = data["choices"][0]["message"]["content"]
        cleaned = sanitize_message_text(raw_content, fallback="[思考中断] 抱歉，我脑子卡壳了，请再问一次。")
        return cleaned[:3000].strip() or "[思考中断] 抱歉，我脑子卡壳了，请再问一次。"
    except Exception as exc:
        raise RuntimeError(f"LLM 返回格式异常: {data}") from exc


# =============================
# 飞书发送模块
# =============================
def send_feishu_message(tenant_access_token: str, open_id: str, text: str) -> None:
    """向指定 open_id 发送飞书文本消息。"""
    if FEISHU_SIMULATE:
        logging.info("[模拟发送] open_id=%s, text=%s", open_id, text)
        return

    if not tenant_access_token:
        raise ValueError("tenant_access_token 不能为空")
    if not open_id:
        raise ValueError("open_id 不能为空")

    text = sanitize_message_text(text)

    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id"
    headers = {
        "Authorization": f"Bearer {tenant_access_token}",
        "Content-Type": "application/json",
    }

    payload = {
        "receive_id": open_id,
        "msg_type": "text",
        # 飞书 text 类型要求 content 是 JSON 字符串
        "content": json.dumps({"text": text}, ensure_ascii=False),
    }

    resp = requests.post(url, headers=headers, json=payload, **build_request_kwargs(15))
    try:
        data = resp.json()
    except Exception:
        data = None

    if resp.status_code >= 400:
        raise RuntimeError(
            f"飞书发消息失败(open_id={open_id}, status={resp.status_code}): "
            f"{data if data is not None else resp.text}"
        )

    if isinstance(data, dict) and data.get("code") != 0:
        raise RuntimeError(f"飞书发消息失败(open_id={open_id}): {data}")


# =============================
# 主流程 + 调度模块
# =============================
def run_daily_job() -> None:
    """单次执行：获取 token -> 逐个用户生成问候 -> 推送消息。"""
    logging.info("开始执行每日问候任务")
    init_memory_db()

    profiles = load_user_profiles()
    if not profiles:
        logging.warning("用户画像为空，跳过本次任务")
        return

    token = get_tenant_access_token(FEISHU_APP_ID, FEISHU_APP_SECRET)
    external_context = fetch_external_context()
    current_time = external_context["time"]
    weather_info = external_context["weather"]
    daily_news = external_context["news"]

    success = 0
    failed = 0

    for profile in profiles:
        open_id = profile.get("open_id", "").strip()
        feature = profile.get("feature", "").strip()

        try:
            recent_memory = get_recent_memory(open_id=open_id, days=3)
            greeting = generate_greeting(
                feature_desc=feature,
                current_time=current_time,
                weather_info=weather_info,
                daily_news=daily_news,
                recent_memory=recent_memory,
            )
            send_feishu_message(token, open_id, greeting)
            save_to_memory(open_id, greeting)
            success += 1
            logging.info("发送成功: open_id=%s, greeting=%s", open_id, greeting)
        except Exception as exc:
            failed += 1
            logging.exception("发送失败: open_id=%s, 错误=%s", open_id, exc)

    logging.info("任务完成: success=%s, failed=%s", success, failed)


def run_digest_job() -> None:
    import sys
    with open("/tmp/digest_debug.log", "a") as f:
        f.write("run_digest_job ENTERED\n")
    print("DEBUG: run_digest_job() started", flush=True)
    sys.stdout.flush()

    """执行 Tech Digest 每日简报推送任务。"""
    logging.info("开始执行 Tech Digest 任务")
    with open("/tmp/digest_debug.log", "a") as f:
        f.write("after logging.info\n")

    try:
        # 延迟导入避免循环依赖
        from memory import init_memory_db as init_memory_db_digest, get_all_active_users
        from tech_digest import run_tech_digest

        init_memory_db_digest()

        users = get_all_active_users()
        if not users:
            logging.warning("活跃用户为空，跳过 Tech Digest 任务")
            return

        success = 0
        failed = 0
        skipped = 0

        for user_id in users:
            try:
                result = run_tech_digest(
                    user_id=user_id,
                    weixin_webhook=WEIXIN_WEBHOOK_URL,
                )
                if result:
                    success += 1
                    logging.info("Tech Digest 推送成功: user_id=%s", user_id)
                else:
                    skipped += 1
                    logging.info("Tech Digest 跳过: user_id=%s (今日已推送或无可用内容)", user_id)
            except Exception as exc:
                failed += 1
                logging.exception("Tech Digest 推送失败: user_id=%s, error=%s", user_id, exc)

        logging.info("Tech Digest 任务完成: success=%s, skipped=%s, failed=%s", success, skipped, failed)

    except Exception as exc:
        logging.error("Tech Digest 任务执行异常: %s", exc)


def start_scheduler() -> None:
    """每天早上执行定时任务。"""
    scheduler = BlockingScheduler(timezone="Asia/Shanghai")

    # 08:05 每日课程推送
    try:
        from learning_scout import push_daily_lesson
        scheduler.add_job(push_daily_lesson, "cron", hour=8, minute=5, id="push_daily_lesson")
        logging.info("每日课程推送调度已注册，将在每天 08:05 执行")
    except Exception as exc:
        logging.warning("每日课程推送调度注册失败: %s", exc)

    if DIGEST_ENABLED:
        try:
            scheduler.add_job(run_digest_job, "cron", hour=8, minute=10, id="dapper_tech_digest")
            logging.info("Tech Digest 调度已注册，将在每天 08:10 执行")
        except Exception as exc:
            logging.warning("Tech Digest 调度注册失败: %s", exc)
    else:
        logging.warning("DIGEST_ENABLED=false，调度器未注册任何任务")

    logging.info("调度器已启动")
    scheduler.start()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Web 服务生命周期：启动时初始化数据库。"""
    init_memory_db()
    yield


app = FastAPI(title="Dapper Coding Feishu Webhook", lifespan=lifespan)

# ============================================================
# APP API Routes (/api/...)  - Learning Scout App API
# ============================================================
from api_routes import router as api_router
app.include_router(api_router)

# ============================================================
# APP Onboarding API (/api/...)  - User Growth System
# ============================================================
from onboarding_backend import router as onboarding_router
app.include_router(onboarding_router)


# ============================================================
# 企业微信回调验证
# ============================================================

WEIXIN_CALLBACK_TOKEN = os.getenv("WEIXIN_CALLBACK_TOKEN", "")
WEIXIN_CALLBACK_AES_KEY = os.getenv("WEIXIN_CALLBACK_AES_KEY", "")


def weixin_verify_signature(signature: str, timestamp: str, nonce: str, encrypt: str) -> bool:
    """验证企业微信签名"""
    if not WEIXIN_CALLBACK_TOKEN:
        return False
    sort_str = ''.join(sorted([WEIXIN_CALLBACK_TOKEN, timestamp, nonce, encrypt]))
    hash_obj = hashlib.sha1(sort_str.encode('utf-8'))
    return hash_obj.hexdigest() == signature


def weixin_decrypt(encrypt_str: str) -> tuple:
    """AES 解密企业微信消息
    
    返回: ( plaintext, from_corpid )
    解密后的 XML 格式: <xml><ToUserName>...</ToUserName><Encrypt>...</Encrypt></xml>
    """
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import unpad
    
    aes_key = base64.b64decode(WEIXIN_CALLBACK_AES_KEY + "=")
    encrypted = base64.b64decode(encrypt_str)
    cipher = AES.new(aes_key, AES.MODE_CBC, iv=encrypted[:16])
    decrypted = unpad(cipher.decrypt(encrypted[16:]), 32)
    return decrypted.decode('utf-8')


def weixin_decrypt_echo(encrypt_str: str) -> str:
    """解密企业微信回调消息，返回明文 XML 内容。

    明文格式：msg_len(4字节, 大端序) + msg_content(msg_len字节)
    企业微信使用这个简单格式（无 random 前缀）。
    """
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import unpad
    import struct

    # Step 1: URL decode
    try:
        decoded_str = unquote(encrypt_str)
        logging.info("URL decode result length: %d", len(decoded_str))
    except Exception as e:
        logging.error("URL decode failed: %s", e)
        decoded_str = encrypt_str

    # Step 2: Base64 decode
    try:
        pad_len = 4 - len(decoded_str) % 4
        if pad_len < 4:
            decoded_str += '=' * pad_len
        encrypted_bytes = base64.b64decode(decoded_str)
        logging.info("Base64 decode success, encrypted length: %d", len(encrypted_bytes))
    except Exception as e:
        logging.error("Base64 decode failed: %s", e)
        raise

    # Step 3: AES 解密
    aes_key = base64.b64decode(WEIXIN_CALLBACK_AES_KEY + "=")
    logging.info("AES key length: %d", len(aes_key))

    if len(encrypted_bytes) < 16:
        raise ValueError("Encrypted data too short")

    iv = encrypted_bytes[:16]
    ciphertext = encrypted_bytes[16:]

    cipher = AES.new(aes_key, AES.MODE_CBC, iv)
    decrypted = cipher.decrypt(ciphertext)

    # Step 4: 去掉 PKCS7 padding
    try:
        decrypted = unpad(decrypted, 16)
    except Exception as exc:
        logging.error("PKCS7 unpad 失败: %s", exc)
        raise
    logging.info("After padding removal, length: %d", len(decrypted))

    # Step 5: 解析明文
    # 尝试两种策略：
    # 策略1：msg_len(4字节大端序) + msg_content
    # 策略2：如果 msg_len 不合理，直接把解密内容当消息
    msg_len = struct.unpack(">I", decrypted[0:4])[0]
    logging.info("msg_len from bytes[0:4] = %d, total_decrypted=%d", msg_len, len(decrypted))

    if 10 < msg_len < 500 and 4 + msg_len <= len(decrypted):
        # 策略1：标准格式
        msg = decrypted[4:4+msg_len].decode('utf-8')
        logging.info("Using strategy 1: msg_len=%d", msg_len)
    else:
        # 策略2：直接返回全部内容（可能是纯XML格式）
        msg = decrypted.decode('utf-8')
        logging.info("Using strategy 2: full content (%d bytes)", len(msg))

    logging.info("Decrypted msg (first 200): %s", repr(msg[:200]))

    return msg


@app.get("/weixin/callback")
def weixin_callback_verify(
    msg_signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...),
    echostr: str = Query(...)
):
    """企业微信 URL 验证回调"""
    try:
        logging.info("收到企业微信验证: sig=%s, ts=%s, nonce=%s, echostr_len=%d", 
                     msg_signature, timestamp, nonce, len(echostr))
        
        plaintext = weixin_decrypt_echo(echostr)
        logging.info("验证成功, plaintext: %s", plaintext[:100])
        return PlainTextResponse(plaintext, status_code=200)
    except Exception as exc:
        logging.error("企业微信验证失败: %s", exc, exc_info=True)
        return PlainTextResponse("error", status_code=500)


def _handle_weixin_feedback(user_id: str, feedback_type: str, is_group: bool, chat_id: str) -> None:
    """处理企业微信用户反馈（拦截正面/负面，不走 LearningAgent）"""
    try:
        from learning_scout import (
            record_learning_event,
            adjust_difficulty_level,
            get_user_current_topic,
        )

        # 1. 记录事件
        record_learning_event(user_id, feedback_type)

        # 2. 获取 direction 并调整难度
        topic, level, direction = get_user_current_topic(user_id)
        if direction:
            new_level = adjust_difficulty_level(user_id, direction)
            reply = f"✅ 收到反馈！课程难度已调整为 {new_level}"
        else:
            reply = "✅ 收到反馈！等你开始学习后自动调整难度"

        # 3. 回复用户确认
        try:
            from weixin_client import get_weixin_client
            client = get_weixin_client()
            if client:
                if is_group:
                    client.send_text_to_chat(reply, chat_id)
                else:
                    client.send_text(reply, to_user=user_id)
        except Exception as exc:
            logging.warning("发送反馈确认消息失败: %s", exc)

    except Exception as exc:
        logging.error("处理用户反馈异常: %s", exc)


@app.post("/weixin/callback")
async def weixin_callback_handle(request: Request):
    """企业微信回调：处理加密消息，调用 LearningAgent 回复用户/群聊
    
    Phase A8: 支持群聊 @机器人 消息
    - ChatId 存在 = 群聊消息，通过 send_text_to_chat 回复到群
    - ChatId 不存在 = 个人消息，通过 send_text 回复用户
    """
    try:
        body = await request.body()
        root = ET.fromstring(body.decode('utf-8'))
        encrypt_elem = root.find('Encrypt')
        if encrypt_elem is None:
            return PlainTextResponse("success")

        encrypt_str = encrypt_elem.text
        decrypted_xml = weixin_decrypt_echo(encrypt_str)
        try:
            msg_root = ET.fromstring(decrypted_xml)
        except Exception as exc:
            logging.error("XML 解析失败，内容前200字符: %s", repr(decrypted_xml[:200]))
            logging.error("XML 解析异常: %s", exc)
            raise

        msg_type = msg_root.findtext('MsgType', '')
        from_user = msg_root.findtext('FromUserName', '')
        chat_id = msg_root.findtext('ChatId', '')  # 群聊ID，存在则为群聊

        logging.info("企业微信消息: type=%s, from=%s, chat=%s", msg_type, from_user, chat_id)

        if msg_type == 'text':
            content_text = msg_root.findtext('Content', '').strip()
            
            if not content_text or not from_user:
                return PlainTextResponse("success")

            # Phase A8: 群聊消息处理
            is_group = bool(chat_id)
            actual_user = msg_root.findtext('ActualUserName', from_user)

            # 从 @Bot 提及中提取真实消息内容
            if content_text.startswith('@') and ' ' in content_text:
                # 格式: "@Bot 你好" -> "你好"
                parts = content_text.split(' ', 1)
                if len(parts) > 1 and parts[0].strip().endswith('Bot'):
                    content_text = parts[1].strip()

            if not content_text:
                return PlainTextResponse("success")

            # 内置命令处理
            if content_text.lower() in ('help', '帮助', '你能做什么', '/help', '功能', 'commands'):
                try:
                    from weixin_client import get_weixin_client
                    wx = get_weixin_client()
                    help_text = """Learning Scout 助手 v2 - 功能一览：

📚 学习陪伴
• 告诉我你想学什么，我会帮你制定学习计划

🔍 AI 问答
• 问任何 AI / 技术问题，我来回答

📰 今日 AI 简报
• 每天 08:10 自动推送 AI 最新资讯

💬 追问
• 对回答不满意，问我"还有呢"

📖 深度阅读
• 简报中的文章可点击链接阅读

直接输入你的问题即可开始！"""
                    if is_group:
                        wx.send_text_to_chat(help_text, chat_id)
                    else:
                        wx.send_text(help_text, to_user=from_user)
                    logging.info("help 命令已回复")
                    return PlainTextResponse("success")
                except Exception as exc:
                    logging.error("help 命令发送失败: %s", exc)
                    return PlainTextResponse("success")

            # 快捷命令处理（仅文本命令，不需要 @Bot 前缀）
            cmd = content_text.lower().strip()
            try:
                from weixin_client import get_weixin_client
                wx = get_weixin_client()
            except Exception:
                wx = None

            if cmd in ('暂停推送', '停止推送', '关闭推送'):
                try:
                    from memory import update_profile
                    update_profile(actual_user, digest_enabled=0)
                    reply = "已关闭每日 AI 简报推送。需要时对我说'恢复推送'即可重新开启。"
                    if wx and is_group:
                        wx.send_text_to_chat(reply, chat_id)
                    elif wx:
                        wx.send_text(reply, to_user=from_user)
                    logging.info("用户 %s 关闭了推送", actual_user)
                    return PlainTextResponse("success")
                except Exception as exc:
                    logging.error("暂停推送失败: %s", exc)

            elif cmd in ('恢复推送', '开启推送', '打开推送'):
                try:
                    from memory import update_profile
                    update_profile(actual_user, digest_enabled=1)
                    reply = "已恢复每日 AI 简报推送！每天 08:10 会准时推送。"
                    if wx and is_group:
                        wx.send_text_to_chat(reply, chat_id)
                    elif wx:
                        wx.send_text(reply, to_user=from_user)
                    logging.info("用户 %s 恢复了推送", actual_user)
                    return PlainTextResponse("success")
                except Exception as exc:
                    logging.error("恢复推送失败: %s", exc)

            elif cmd in ('查看进度', '我的进度', '学习进度'):
                try:
                    from memory import get_profile
                    profile = get_profile(actual_user)
                    interests = profile.关注领域 or "未设置"
                    difficulty = profile.难度偏好 or "未设置"
                    reply = f"""Learning Scout v2 - 当前设置：

关注领域：{interests}
难度偏好：{difficulty}

发送「暂停推送」可关闭每日简报。"""
                    if wx and is_group:
                        wx.send_text_to_chat(reply, chat_id)
                    elif wx:
                        wx.send_text(reply, to_user=from_user)
                    return PlainTextResponse("success")
                except Exception as exc:
                    logging.error("查看进度失败: %s", exc)

            # 反馈检测：拦截正面/负面反馈，不走 LearningAgent
            positive_keys = {'👍', '好', '有用', '赞', '很棒', '不错', '喜欢', 'like', 'great', 'good'}
            negative_keys = {'👎', '差', '没用', '一般', '不好', 'bad', 'dislike', '不喜欢', '失望'}
            content_lower = content_text.lower().strip()
            if content_lower in positive_keys:
                _handle_weixin_feedback(actual_user, "positive_feedback", is_group, chat_id)
                return PlainTextResponse("success")
            elif content_lower in negative_keys:
                _handle_weixin_feedback(actual_user, "negative_feedback", is_group, chat_id)
                return PlainTextResponse("success")

            # 调用 LearningAgent 生成回复
            try:
                from learning_agent import get_learning_agent
                agent = get_learning_agent()
                reply_text = agent.process_message(actual_user, 'wechat_group' if is_group else 'wechat', content_text)
                logging.info("LearningAgent 回复长度: %d", len(reply_text))
            except Exception as exc:
                logging.error("LearningAgent 调用失败: %s", exc)
                reply_text = "抱歉，助手暂时无法回复，请稍后再试。"

            # 通过企业微信 API 发送回复
            try:
                from weixin_client import get_weixin_client
                wx = get_weixin_client()
                if wx is None:
                    logging.error("企业微信客户端初始化失败")
                elif is_group:
                    # 群聊回复：发送到群
                    ok = wx.send_text_to_chat(reply_text, chat_id)
                    logging.info("发送群聊回复结果(chat=%s): %s", chat_id, ok)
                else:
                    # 个人回复
                    ok = wx.send_text(reply_text, to_user=from_user)
                    logging.info("发送个人回复结果: %s", ok)
            except Exception as exc:
                logging.error("发送企业微信消息失败: %s", exc)

        elif msg_type == 'event':
            event = msg_root.findtext('Event', '')
            event_key = msg_root.findtext('EventKey', '')
            logging.info("事件: event=%s, key=%s", event, event_key)
            if event == 'CLICK':
                positive_keys = {'praise', 'thumb_up', 'positive', 'like', 'good', '有用', '点赞', '棒'}
                negative_keys = {'negative', 'thumb_down', 'bad', 'dislike', '差', '没用', '一般', '吐槽'}
                is_group = bool(chat_id)
                if event_key.lower() in positive_keys:
                    _handle_weixin_feedback(from_user, "positive_feedback", is_group, chat_id)
                elif event_key.lower() in negative_keys:
                    _handle_weixin_feedback(from_user, "negative_feedback", is_group, chat_id)


        
        elif msg_type == 'image':
            # WeChat: 图片消息 -> 下载 + OCR -> LearningAgent 回复
            is_group = bool(chat_id)
            actual_user = msg_root.findtext('ActualUserName', from_user)
            media_id = msg_root.findtext('MediaId', '')
            ocr_text = ''
            if media_id:
                try:
                    from weixin_client import get_weixin_client
                    wx_client = get_weixin_client()
                    token = wx_client._get_access_token() if wx_client else None
                    if token:
                        import requests as _req
                        media_url = (
                            'https://qyapi.weixin.qq.com/cgi-bin/media/get'
                            '?access_token=' + token + '&media_id=' + media_id
                        )
                        img_resp = _req.get(media_url, timeout=15)
                        if img_resp.status_code == 200 and 'image' in img_resp.headers.get('Content-Type', ''):
                            import io as _io
                            from PIL import Image
                            img = Image.open(_io.BytesIO(img_resp.content))
                            try:
                                import pytesseract
                                ocr_text = pytesseract.image_to_string(img, lang='chi_sim+eng').strip()
                                if ocr_text:
                                    logging.info('WeChat OCR 成功: %d 字符', len(ocr_text))
                            except Exception as ocr_exc:
                                logging.warning('WeChat OCR 失败: %s', ocr_exc)
                        else:
                            logging.warning('WeChat 图片下载失败: status=%d', img_resp.status_code)
                except Exception as img_exc:
                    logging.warning('WeChat 图片处理异常: %s', img_exc)
            # 通过 LearningAgent 生成智能回复
            ocr_message = '[用户发送了图片，OCR识别结果：' + (ocr_text if ocr_text else '无法识别') + ']'
            try:
                from learning_agent import get_learning_agent
                agent = get_learning_agent()
                reply_text = agent.process_message(
                    actual_user,
                    'wechat_group' if is_group else 'wechat',
                    ocr_message
                )
            except Exception as exc:
                logging.error('LearningAgent 图片处理失败: %s', exc)
                reply_text = '[收到图片，但无法识别内容。请换一张更清晰的图片试试～]'
            # 发送回复
            try:
                from weixin_client import get_weixin_client
                wx = get_weixin_client()
                if wx and is_group:
                    wx.send_text_to_chat(reply_text, chat_id)
                elif wx:
                    wx.send_text(reply_text, to_user=from_user)
            except Exception as exc:
                logging.error('发送图片回复失败: %s', exc)
        return PlainTextResponse("success")

    except Exception as exc:
        logging.error("处理企业微信回调异常: %s", exc)
        return PlainTextResponse("success")



def _verify_admin_basic_auth(auth_header: str) -> bool:
    """校验 /admin 的 HTTP Basic 凭据。"""
    if not WEB_ADMIN_PASSWORD:
        return False
    if not auth_header or not auth_header.startswith("Basic "):
        return False
    token = auth_header.split(" ", 1)[1].strip()
    try:
        decoded = base64.b64decode(token).decode("utf-8", errors="ignore")
    except Exception:
        return False
    if ":" not in decoded:
        return False
    username, password = decoded.split(":", 1)
    return secrets.compare_digest(username, "admin") and secrets.compare_digest(password, WEB_ADMIN_PASSWORD)


@app.middleware("http")
async def admin_auth_middleware(request: Request, call_next):
    """为 /admin 静态页面统一加 Basic Auth。"""
    path = request.url.path
    if WEB_ENABLED and path.startswith("/admin"):
        if not WEB_ADMIN_PASSWORD:
            return Response("WEB_ADMIN_PASSWORD 未配置", status_code=500)
        if not _verify_admin_basic_auth(request.headers.get("Authorization", "")):
            return Response(
                "认证失败",
                status_code=401,
                headers={"WWW-Authenticate": "Basic"},
            )
    return await call_next(request)


if WEB_ENABLED:
    try:
        admin_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "admin")
        build_path = os.path.join(admin_root, "build")
        dist_path = os.path.join(admin_root, "dist")
        fallback_path = os.path.join(admin_root, "_1")

        serve_path = ""
        if os.path.isdir(build_path):
            serve_path = build_path
        elif os.path.isdir(dist_path):
            serve_path = dist_path
        elif os.path.isdir(fallback_path):
            serve_path = fallback_path

        if serve_path:
            app.mount("/admin", StaticFiles(directory=serve_path, html=True), name="admin")
            logging.info("Web 管理界面已挂载：/admin -> %s", serve_path)
        else:
            logging.warning("admin 前端目录不存在(build/dist/_1)，Web 管理界面不可用")
    except Exception as exc:
        logging.error("挂载 Web 管理界面失败：%s", exc)


class LearningSearchRequest(BaseModel):
    query: str
    top_k: int = 5


class SeriesListRequest(BaseModel):
    series_id: str


class LearningFeedbackRequest(BaseModel):
    item_id: int
    open_id: str
    action: str

class FeedbackRequest(BaseModel):
    """Tech Digest 反馈请求"""
    user_id: str
    action: str  # click/like/dislike/too_hard/too_easy
    item_id: Optional[int] = None
    feedback_text: Optional[str] = ""

class RegisterUserRequest(BaseModel):
    user_id: str
    关注领域: Optional[str] = ""
    难度偏好: Optional[str] = "入门"
    weixin_webhook: Optional[str] = ""

class SetDigestEnabledRequest(BaseModel):
    user_id: str
    enabled: bool

class DigestProfileRequest(BaseModel):
    """Digest 偏好设置请求"""
    user_id: str
    关注领域: Optional[str] = None
    难度偏好: Optional[str] = None
    阅读深度偏好: Optional[str] = None


RAG_KEYWORDS = ["总结", "介绍一下", "什么是", "怎么做", "为什么", "帮我", "解释", "讲讲"]


class RunWorkflowResponse(BaseModel):
    status: str
    fetched: int = 0
    saved: int = 0
    skipped_ads: int = 0
    skipped_duplicates: int = 0
    embeddings_generated: int = 0
    errors: List[str] = []


class AskRequest(BaseModel):
    question: str
    top_k: int = 10


class AskResponse(BaseModel):
    answer: str
    citations: List[Dict[str, str]]
    total: int


@app.post("/learning/search", response_model=dict)
def learning_search(body: LearningSearchRequest) -> dict:
    """语义搜索学习资料库。"""
    try:
        from learning_scout import EMBEDDING_ENABLED, search_by_embedding
    except Exception as exc:
        logging.error("导入 learning_scout 失败：%s", exc)
        return {"items": [], "total": 0, "error": "模块导入失败"}

    if not EMBEDDING_ENABLED:
        return {"items": [], "total": 0, "error": "EMBEDDING_ENABLED=false"}

    try:
        items = search_by_embedding(body.query, body.top_k)
        for item in items:
            item["tags"] = [str(t) for t in item.get("tags", [])]
        return {"items": items, "total": len(items)}
    except Exception as exc:
        logging.error("learning_search 失败：%s", exc)
        return {"items": [], "total": 0, "error": str(exc)}


@app.post("/learning/feedback", response_model=dict)
def learning_feedback(body: LearningFeedbackRequest) -> dict:
    """记录用户反馈（click/ignore）。"""
    try:
        from learning_scout import record_feedback

        record_feedback(body.item_id, body.open_id, body.action)
        return {"ok": True}
    except Exception as exc:
        logging.error("learning_feedback 失败：%s", exc)
        return {"ok": False, "error": str(exc)}


@app.post("/digest/feedback", response_model=dict)
def digest_feedback(body: FeedbackRequest) -> dict:
    """记录用户对 Tech Digest 简报的反馈，更新偏好。
    
    反馈类型：
    - click: 用户点击了推荐的某篇文章
    - like: 用户表示喜欢这篇简报
    - dislike: 用户表示不喜欢这篇简报
    - too_hard: 用户反馈内容太难
    - too_easy: 用户反馈内容太简单
    """
    try:
        from tech_digest import learn_from_feedback

        learn_from_feedback(
            user_id=body.user_id,
            action=body.action,
            feedback_text=body.feedback_text or "",
        )
        logging.info("digest_feedback 成功: user=%s action=%s", body.user_id, body.action)
        return {"ok": True}
    except Exception as exc:
        logging.error("digest_feedback 失败: user=%s action=%s error=%s", body.user_id, body.action, exc)
        return {"ok": False, "error": str(exc)}


@app.post("/users/register", response_model=dict)
def users_register(body: RegisterUserRequest) -> dict:
    """注册新用户或更新已有用户配置"""
    try:
        from memory import register_user
        
        register_user(
            user_id=body.user_id,
            关注领域=body.关注领域 or "",
            难度偏好=body.难度偏好 or "入门",
            weixin_webhook=body.weixin_webhook or "",
        )
        logging.info("users_register 成功: user_id=%s", body.user_id)
        return {"ok": True, "user_id": body.user_id}
    except Exception as exc:
        logging.error("users_register 失败: user_id=%s error=%s", body.user_id, exc)
        return {"ok": False, "error": str(exc)}


@app.post("/users/set-digest", response_model=dict)
def users_set_digest(body: SetDigestEnabledRequest) -> dict:
    """启用/禁用用户的 Digest 推送"""
    try:
        from memory import set_digest_enabled
        
        set_digest_enabled(body.user_id, body.enabled)
        logging.info("users_set_digest 成功: user_id=%s enabled=%s", body.user_id, body.enabled)
        return {"ok": True, "user_id": body.user_id, "enabled": body.enabled}
    except Exception as exc:
        logging.error("users_set_digest 失败: user_id=%s error=%s", body.user_id, exc)
        return {"ok": False, "error": str(exc)}


@app.get("/users/list", response_model=dict)
def users_list() -> dict:
    """列出所有用户及其状态"""
    try:
        from memory import get_all_active_users, init_memory_db
        import sqlite3
        
        init_memory_db()
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM user_profiles ORDER BY created_at DESC").fetchall()
        
        users = []
        for row in rows:
            users.append({
                "user_id": row["user_id"],
                "关注领域": row["关注领域"] if row["关注领域"] else "",
                "难度偏好": row["难度偏好"] if row["难度偏好"] else "入门",
                "digest_enabled": bool(row["digest_enabled"]) if row["digest_enabled"] else False,
                "created_at": row["created_at"] if row["created_at"] else "",
            })
        
        return {"ok": True, "users": users, "total": len(users)}
    except Exception as exc:
        logging.error("users_list 失败: %s", exc)
        return {"ok": False, "error": str(exc), "users": [], "total": 0}


@app.delete("/users/{user_id}", response_model=dict)
def users_delete(user_id: str) -> dict:
    """删除用户（禁用 Digest）"""
    try:
        from memory import set_digest_enabled
        
        set_digest_enabled(user_id, False)
        logging.info("users_delete 成功: user_id=%s", user_id)
        return {"ok": True, "user_id": user_id}
    except Exception as exc:
        logging.error("users_delete 失败: user_id=%s error=%s", user_id, exc)
        return {"ok": False, "error": str(exc)}



@app.post("/users/register", response_model=dict)
def users_register(body: RegisterUserRequest) -> dict:
    """注册新用户或更新已有用户配置"""
    try:
        from memory import register_user
        
        register_user(
            user_id=body.user_id,
            关注领域=body.关注领域 or "",
            难度偏好=body.难度偏好 or "入门",
            weixin_webhook=body.weixin_webhook or "",
        )
        logging.info("users_register 成功: user_id=%s", body.user_id)
        return {"ok": True, "user_id": body.user_id}
    except Exception as exc:
        logging.error("users_register 失败: user_id=%s error=%s", body.user_id, exc)
        return {"ok": False, "error": str(exc)}


@app.post("/users/set-digest", response_model=dict)
def users_set_digest(body: SetDigestEnabledRequest) -> dict:
    """启用/禁用用户的 Digest 推送"""
    try:
        from memory import set_digest_enabled
        
        set_digest_enabled(body.user_id, body.enabled)
        logging.info("users_set_digest 成功: user_id=%s enabled=%s", body.user_id, body.enabled)
        return {"ok": True, "user_id": body.user_id, "enabled": body.enabled}
    except Exception as exc:
        logging.error("users_set_digest 失败: user_id=%s error=%s", body.user_id, exc)
        return {"ok": False, "error": str(exc)}


@app.get("/users/list", response_model=dict)
def users_list() -> dict:
    """列出所有用户及其状态"""
    try:
        from memory import get_all_active_users, init_memory_db
        import sqlite3
        
        init_memory_db()
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM user_profiles ORDER BY created_at DESC").fetchall()
        
        users = []
        for row in rows:
            users.append({
                "user_id": row["user_id"],
                "关注领域": row["关注领域"] if row["关注领域"] else "",
                "难度偏好": row["难度偏好"] if row["难度偏好"] else "入门",
                "digest_enabled": bool(row["digest_enabled"]) if row["digest_enabled"] else False,
                "created_at": row["created_at"] if row["created_at"] else "",
            })
        
        return {"ok": True, "users": users, "total": len(users)}
    except Exception as exc:
        logging.error("users_list 失败: %s", exc)
        return {"ok": False, "error": str(exc), "users": [], "total": 0}


@app.delete("/users/{user_id}", response_model=dict)
def users_delete(user_id: str) -> dict:
    """删除用户（禁用 Digest）"""
    try:
        from memory import set_digest_enabled
        
        set_digest_enabled(user_id, False)
        logging.info("users_delete 成功: user_id=%s", user_id)
        return {"ok": True, "user_id": user_id}
    except Exception as exc:
        logging.error("users_delete 失败: user_id=%s error=%s", user_id, exc)
        return {"ok": False, "error": str(exc)}

@app.post("/digest/profile", response_model=dict)
def digest_profile(body: DigestProfileRequest) -> dict:
    """获取或更新用户的 Digest 偏好设置。
    
    - GET: 不传任何偏好字段则返回当前偏好
    - UPDATE: 传入任意偏好字段则更新
    """
    try:
        from memory import get_profile, update_profile as memory_update_profile

        if body.关注领域 or body.难度偏好 or body.阅读深度偏好:
            # 更新偏好
            updates = {}
            if body.关注领域 is not None:
                updates["关注领域"] = body.关注领域
            if body.难度偏好 is not None:
                updates["难度偏好"] = body.难度偏好
            if body.阅读深度偏好 is not None:
                updates["阅读深度偏好"] = body.阅读深度偏好
            
            memory_update_profile(body.user_id, **updates)
            logging.info("digest_profile 更新成功: user=%s updates=%s", body.user_id, list(updates.keys()))
            return {"ok": True, "profile": get_profile(body.user_id).__dict__}
        else:
            # 获取当前偏好
            profile = get_profile(body.user_id)
            return {"ok": True, "profile": {
                "user_id": profile.user_id,
                "关注领域": profile.关注领域,
                "难度偏好": profile.难度偏好,
                "阅读深度偏好": profile.阅读深度偏好,
                "热度权重": profile.get_热度权重_dict(),
            }}
    except Exception as exc:
        logging.error("digest_profile 失败: user=%s error=%s", body.user_id, exc)
        return {"ok": False, "error": str(exc)}


@app.post("/learning/series", response_model=dict)
def learning_series(body: SeriesListRequest) -> dict:
    """获取某个系列的所有资料。"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT id, title, url, summary, tags, published_at, click_count
                FROM learning_scout_items
                WHERE series_id = ?
                ORDER BY published_at ASC
                """,
                (body.series_id,),
            ).fetchall()

        items = []
        for row in rows:
            tags = []
            try:
                tags = json.loads(row["tags"]) if isinstance(row["tags"], str) else []
            except Exception:
                pass
            items.append(
                {
                    "id": row["id"],
                    "title": row["title"],
                    "url": row["url"],
                    "summary": row["summary"],
                    "tags": tags,
                    "published_at": row["published_at"],
                    "click_count": row["click_count"],
                }
            )

        return {"items": items, "total": len(items), "series_id": body.series_id}
    except Exception as exc:
        logging.error("learning_series 失败：%s", exc)
        return {"items": [], "total": 0, "error": str(exc)}


@app.get("/learning/feed-recommendations", response_model=dict)
def learning_feed_recommendations() -> dict:
    """推荐相似主题的订阅源。"""
    try:
        from learning_scout import load_feeds, recommend_similar_feeds

        existing = load_feeds()
        recs = recommend_similar_feeds(existing, limit=5)
        return {"recommendations": recs, "total": len(recs)}
    except Exception as exc:
        logging.error("learning_feed_recommendations 失败：%s", exc)
        return {"recommendations": [], "total": 0, "error": str(exc)}


@app.post("/learning/run", response_model=dict)
def learning_run() -> dict:
    """手动触发学习工作流（供 supervisor Agent 或用户调用）。"""
    try:
        from learning_scout import WORKFLOW_ENABLED, run_learning_scout_workflow
    except Exception as exc:
        logging.error("导入 learning_scout 失败：%s", exc)
        return {"status": "failed", "error": "模块导入失败"}

    if not WORKFLOW_ENABLED:
        return {"status": "skipped", "error": "WORKFLOW_ENABLED=false"}

    try:
        result = run_learning_scout_workflow()
        if not isinstance(result, dict):
            return {"status": "success", "message": "工作流执行完成，详见日志"}
        return result
    except Exception as exc:
        logging.error("learning_run 执行失败：%s", exc)
        return {"status": "failed", "error": str(exc)}


@app.post("/digest/run", response_model=dict)
def digest_run() -> dict:
    """手动触发 Tech Digest 任务（供测试或 supervisor Agent 调用）。"""
    if not DIGEST_ENABLED:
        return {"status": "skipped", "error": "DIGEST_ENABLED=false"}

    try:
        run_digest_job()
        return {"status": "success", "message": "Tech Digest 执行完成，详见日志"}
    except Exception as exc:
        logging.error("digest_run 执行失败：%s", exc)
        return {"status": "failed", "error": str(exc)}


@app.post("/learning/ask", response_model=dict)
def learning_ask(body: AskRequest) -> dict:
    """RAG 问答：基于资料库回答问题。"""
    try:
        from learning_scout import RAG_ENABLED, build_rag_context, generate_rag_answer, search_by_embedding
    except Exception as exc:
        logging.error("导入 learning_scout 失败：%s", exc)
        return {"answer": "模块导入失败", "citations": [], "total": 0, "error": str(exc)}

    if not RAG_ENABLED:
        return {"answer": "RAG 问答功能已关闭", "citations": [], "total": 0}

    try:
        context, items = build_rag_context(body.question, body.top_k)
        if not items:
            return {"answer": "未找到相关资料，建议换关键词试试。", "citations": [], "total": 0}

        answer = generate_rag_answer(body.question, context)
        citations = []
        for i, item in enumerate(items, 1):
            citations.append(
                {
                    "index": i,
                    "title": str(item.get("title", "")),
                    "url": str(item.get("url", "")),
                }
            )

        return {"answer": answer, "citations": citations, "total": len(citations)}
    except Exception as exc:
        logging.error("learning_ask 失败：%s", exc)
        return {"answer": "回答生成失败", "citations": [], "total": 0, "error": str(exc)}


def verify_feishu_event_token(event_payload: dict) -> bool:
    """校验飞书事件回调中的 token，未通过时返回 False。"""
    if not FEISHU_VERIFY_ENABLED:
        return True

    try:
        header = event_payload.get("header") if isinstance(event_payload, dict) else None
        event = event_payload.get("event") if isinstance(event_payload, dict) else None

        candidate = ""
        if isinstance(header, dict):
            candidate = str(header.get("token", "")).strip()
        if not candidate and isinstance(event, dict):
            candidate = str(event.get("token", "")).strip()
        if not candidate:
            candidate = str(event_payload.get("token", "")).strip() if isinstance(event_payload, dict) else ""

        if not candidate:
            logging.warning("飞书事件校验失败：payload 中未找到 token")
            return False

        if candidate != FEISHU_VERIFICATION_TOKEN:
            logging.warning("飞书事件校验失败：token 不匹配")
            return False

        return True
    except Exception as exc:
        logging.warning("飞书事件校验异常：%s", exc)
        return False


def build_feishu_challenge_response(body_text: str) -> Optional[str]:
    """处理飞书 URL 验证 challenge，返回响应 JSON 字符串；非 challenge 请求返回 None。"""
    try:
        payload = json.loads(body_text)
    except Exception:
        return None

    if not isinstance(payload, dict):
        return None

    challenge = payload.get("challenge")
    if not challenge:
        return None

    if not verify_feishu_event_token(payload):
        raise ValueError("飞书 challenge 校验失败：token 不匹配")

    return json.dumps({"challenge": challenge}, ensure_ascii=False)


def log_non_challenge_event(body_text: str) -> None:
    """记录普通飞书事件，避免阻塞主请求。"""
    logging.info("收到飞书普通事件: %s", body_text[:500])


def handle_feishu_message(body_text: str) -> None:
    """处理飞书消息事件：解析文本、生成回复并回写记忆。"""
    try:
        payload = json.loads(body_text)
        if not isinstance(payload, dict):
            logging.info("飞书事件不是字典结构，已忽略")
            save_feishu_inbound_event(status="ignored", error="payload is not dict", raw_body=body_text)
            return

        dedup_key = build_feishu_dedup_key(payload, body_text)
        if not register_feishu_event_once(dedup_key):
            logging.info("飞书事件已重复，跳过处理(dedup_key=%s)", dedup_key)
            header = payload.get("header") if isinstance(payload.get("header"), dict) else {}
            event = payload.get("event") if isinstance(payload.get("event"), dict) else {}
            message = event.get("message") if isinstance(event.get("message"), dict) else {}
            sender = event.get("sender") if isinstance(event.get("sender"), dict) else {}
            sender_id = sender.get("sender_id") if isinstance(sender.get("sender_id"), dict) else {}
            open_id = (
                str(sender_id.get("open_id", "")).strip()
                or str(sender.get("open_id", "")).strip()
                or str(event.get("open_id", "")).strip()
            )
            save_feishu_inbound_event(
                dedup_key=dedup_key,
                event_type=str((header or {}).get("event_type", "")).strip(),
                open_id=open_id,
                message_type=str((message or {}).get("message_type", "")).strip(),
                user_text="",
                status="duplicate",
                error="duplicate event",
                raw_body=body_text,
            )
            return

        header = payload.get("header") if isinstance(payload.get("header"), dict) else {}
        event_type = str(header.get("event_type", "")).strip()
        if event_type != "im.message.receive_v1":
            logging.info("飞书事件已忽略(event_type=%s)", event_type or "unknown")
            save_feishu_inbound_event(
                dedup_key=dedup_key,
                event_type=event_type,
                status="ignored",
                error=f"event_type={event_type or 'unknown'}",
                raw_body=body_text,
            )
            return

        event = payload.get("event") if isinstance(payload.get("event"), dict) else {}
        message = event.get("message") if isinstance(event.get("message"), dict) else {}

        # 1. Extract open_id first (needed for image reply)
        sender = event.get("sender") if isinstance(event.get("sender"), dict) else {}
        sender_id = sender.get("sender_id") if isinstance(sender.get("sender_id"), dict) else {}
        open_id = (
            str(sender_id.get("open_id", "")).strip()
            or str(sender.get("open_id", "")).strip()
            or str(event.get("open_id", "")).strip()
        )

        # 2. Check message type
        msg_type = str(message.get("message_type", "")).strip()

        if msg_type == "image":
            # Image: download from Feishu API + OCR -> reply to user
            image_key = ""
            try:
                import json
                content_obj = json.loads(message.get("content", "{}"))
                image_key = content_obj.get("image_key", "") if isinstance(content_obj, dict) else ""
            except:
                pass

            ocr_text = ""
            reply_text = "[收到图片，但无法识别内容。请换一张更清晰的图片试试～]"

            if image_key:
                try:
                    token = get_tenant_access_token(FEISHU_APP_ID, FEISHU_APP_SECRET)
                    img_url = "https://open.feishu.cn/open-apis/im/v1/images/" + image_key
                    img_resp = requests.get(
                        img_url,
                        headers={"Authorization": "Bearer " + token},
                        timeout=15
                    )
                    if img_resp.status_code == 200:
                        import io as _io
                        from PIL import Image
                        img = Image.open(_io.BytesIO(img_resp.content))
                        try:
                            import pytesseract
                            ocr_text = pytesseract.image_to_string(img, lang="chi_sim+eng").strip()
                            if ocr_text:
                                logging.info("图片 OCR 成功: %d 字符", len(ocr_text))
                        except Exception as ocr_exc:
                            logging.warning("图片 OCR 失败: %s", ocr_exc)
                    else:
                        logging.warning("图片下载失败: status=%d", img_resp.status_code)
                except Exception as img_exc:
                    logging.warning("图片处理异常: %s", img_exc)

            if ocr_text:
                reply_text = (
                    "【图片识别结果】\n\n" + ocr_text +
                    "\n\n如果你想了解图片内容，可以直接问我～"
                )

            token = get_tenant_access_token(FEISHU_APP_ID, FEISHU_APP_SECRET)
            send_feishu_message(token, open_id, reply_text)
            save_feishu_inbound_event(
                dedup_key=dedup_key,
                event_type=event_type,
                open_id=open_id,
                message_type="image",
                user_text="[图片 OCR: " + (ocr_text[:100] if ocr_text else "无法识别") + "]",
                status="image_replied",
                raw_body=body_text,
            )
            return

        elif msg_type != "text":
            logging.info("飞书消息已忽略(message_type=%s)", msg_type)
            save_feishu_inbound_event(
                dedup_key=dedup_key,
                event_type=event_type,
                open_id=open_id,
                message_type=msg_type,
                status="ignored",
                error="message_type=" + msg_type,
                raw_body=body_text,
            )
            return

        # 3. Parse text content
        content_raw = message.get("content", "")
        user_text = ""
        try:
            content_obj = json.loads(content_raw) if isinstance(content_raw, str) else content_raw
            if isinstance(content_obj, dict):
                user_text = str(content_obj.get("text", "")).strip()
        except Exception as exc:
            logging.warning("解析消息 content 失败(open_id=%s): %s", open_id, exc)
            save_feishu_inbound_event(
                dedup_key=dedup_key,
                event_type=event_type,
                open_id=open_id,
                message_type=str(message.get("message_type", "")).strip(),
                status="parse_error",
                error=str(exc),
                raw_body=body_text,
            )
            return

        if not user_text:
            logging.info("用户文本消息为空(open_id=%s)，已忽略", open_id)
            save_feishu_inbound_event(
                dedup_key=dedup_key,
                event_type=event_type,
                open_id=open_id,
                message_type=str(message.get("message_type", "")).strip(),
                status="ignored",
                error="empty user text",
                raw_body=body_text,
            )
            return
        intent = "unknown"
        current_state = ""
        onboarding_intents = {"new_user", "direction_selected", "path_confirmed", "path_rejected", "time_selected"}
        try:
            from learning_scout import detect_intent, get_user_conversation, handle_fear, handle_onboarding

            conv = get_user_conversation(open_id)
            current_state = str(conv.get("state") or "")
            intent = detect_intent(user_text, current_state=current_state)

            if intent in onboarding_intents:
                reply_text = handle_onboarding(open_id, user_text)
                if reply_text:
                    token = get_tenant_access_token(FEISHU_APP_ID, FEISHU_APP_SECRET)
                    send_feishu_message(token, open_id, reply_text)
                    save_to_memory(open_id, f"onboarding({current_state}->{intent})：{user_text} | 回复：{reply_text}")
                    save_feishu_inbound_event(
                        dedup_key=dedup_key,
                        event_type=event_type,
                        open_id=open_id,
                        message_type=str(message.get("message_type", "")).strip(),
                        user_text=user_text,
                        status="onboarding_replied",
                        raw_body=body_text,
                    )
                    return

            if intent == "fear_hard":
                reply_text = handle_fear(open_id, user_text)
                token = get_tenant_access_token(FEISHU_APP_ID, FEISHU_APP_SECRET)
                send_feishu_message(token, open_id, reply_text)
                save_to_memory(open_id, f"用户畏难：{user_text} | 安抚：{reply_text}")
                save_feishu_inbound_event(
                    dedup_key=dedup_key,
                    event_type=event_type,
                    open_id=open_id,
                    message_type=str(message.get("message_type", "")).strip(),
                    user_text=user_text,
                    status="fear_replied",
                    raw_body=body_text,
                )
                return
        except Exception as exc:
            logging.warning("Phase7 onboarding 分流失败，将回退旧逻辑(open_id=%s): %s", open_id, exc)

        search_keywords = ["找", "搜索", "查一下", "有没有", "帮我找"]
        if any(keyword in user_text for keyword in search_keywords):
            query = user_text
            for keyword in search_keywords:
                query = query.replace(keyword, "")
            query = query.strip()
            if query:
                try:
                    from learning_scout import search_by_embedding

                    results = search_by_embedding(query, top_k=5)
                except Exception as exc:
                    logging.warning("飞书搜索失败：%s", exc)
                    results = []

                if results:
                    lines = ["搜索「{}」，找到 {} 条相关资料：".format(query, len(results))]
                    for index, item in enumerate(results, 1):
                        title = str(item.get("title", "未命名")).strip()
                        url = str(item.get("url", "")).strip()
                        summary = str(item.get("summary", "")).strip()
                        tags = item.get("tags", []) if isinstance(item.get("tags"), list) else []
                        tag_str = " ".join(["#{}".format(str(tag).strip()) for tag in tags if str(tag).strip()])
                        lines.append("{}. {}（{}）".format(index, title, url))
                        if summary:
                            lines.append("   {}".format(summary))
                        if tag_str:
                            lines.append("   {}".format(tag_str))
                    reply_text = "\n".join(lines).strip()
                else:
                    reply_text = "搜索「{}」未找到相关资料。".format(query)

                token = get_tenant_access_token(FEISHU_APP_ID, FEISHU_APP_SECRET)
                send_feishu_message(token, open_id, reply_text)
                save_to_memory(open_id, "用户搜索：{} | 结果：{}条".format(query, len(results)))
                save_feishu_inbound_event(
                    dedup_key=dedup_key,
                    event_type=event_type,
                    open_id=open_id,
                    message_type=str(message.get("message_type", "")).strip(),
                    user_text=user_text,
                    status="search_replied",
                    raw_body=body_text,
                )
                return

        if intent == "ask_question" or any(keyword in user_text for keyword in RAG_KEYWORDS):
            question = user_text
            try:
                from learning_scout import rag_qa

                answer, citations = rag_qa(question)
                reply_text = f"{answer}{citations}" if citations else answer
            except Exception as exc:
                logging.warning("飞书 RAG 问答失败：%s", exc)
                reply_text = "抱歉，回答生成失败，请稍后再试。"

            token = get_tenant_access_token(FEISHU_APP_ID, FEISHU_APP_SECRET)
            send_feishu_message(token, open_id, reply_text)
            save_to_memory(open_id, "用户 RAG 问答：{} | 回答：{}字".format(question, len(reply_text)))
            save_feishu_inbound_event(
                dedup_key=dedup_key,
                event_type=event_type,
                open_id=open_id,
                message_type=str(message.get("message_type", "")).strip(),
                user_text=user_text,
                status="rag_replied",
                raw_body=body_text,
            )
            return

        recent_memory = get_recent_memory(open_id=open_id, days=3)
        reply_text = generate_chat_reply(user_text, recent_memory)
        token = get_tenant_access_token(FEISHU_APP_ID, FEISHU_APP_SECRET)
        send_feishu_message(token, open_id, reply_text)
        save_to_memory(open_id, f"用户问：{user_text} | Agent答：{reply_text}")
        save_feishu_inbound_event(
            dedup_key=dedup_key,
            event_type=event_type,
            open_id=open_id,
            message_type=str(message.get("message_type", "")).strip(),
            user_text=user_text,
            status="replied",
            raw_body=body_text,
        )
        logging.info("飞书消息处理成功(open_id=%s, user_text=%s)", open_id, user_text)
    except Exception as exc:
        logging.error("处理飞书消息失败: %s", exc, exc_info=True)
        try:
            save_feishu_inbound_event(status="error", error=str(exc), raw_body=body_text)
        except Exception:
            pass


@app.post("/feishu/webhook")
async def feishu_webhook(request: Request, background_tasks: BackgroundTasks) -> dict:
    """飞书回调入口：处理 challenge 校验与普通事件回执。"""
    body_text = (await request.body()).decode("utf-8", errors="ignore")

    challenge_resp = build_feishu_challenge_response(body_text)
    if challenge_resp:
        return json.loads(challenge_resp)

    background_tasks.add_task(handle_feishu_message, body_text)
    return {"msg": "ok"}


@app.get("/feishu/events")
def feishu_events(limit: int = 20) -> dict:
    """查看最近收到的飞书入站消息。"""
    return {"items": get_recent_feishu_events(limit=limit)}


@app.get("/feishu/events/view", response_class=HTMLResponse)
def feishu_events_view(limit: int = 20) -> str:
    """可视化查看最近飞书入站消息。"""
    items = get_recent_feishu_events(limit=limit)

    rows = []
    for item in items:
        status = html.escape(str(item.get("status", "")))
        created_at = html.escape(str(item.get("created_at", "")))
        event_type = html.escape(str(item.get("event_type", "")))
        open_id = html.escape(str(item.get("open_id", "")))
        message_type = html.escape(str(item.get("message_type", "")))
        user_text = html.escape(str(item.get("user_text", "")))
        error = html.escape(str(item.get("error", "")))

        rows.append(
            "<tr>"
            f"<td>{created_at}</td>"
            f"<td>{status}</td>"
            f"<td>{event_type}</td>"
            f"<td>{message_type}</td>"
            f"<td>{open_id}</td>"
            f"<td>{user_text}</td>"
            f"<td>{error}</td>"
            "</tr>"
        )

    table_body = "".join(rows) if rows else "<tr><td colspan='7'>暂无记录</td></tr>"
    return f"""
<!doctype html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <meta http-equiv=\"refresh\" content=\"5\" />
  <title>Feishu Events Dashboard</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 16px; }}
    h2 {{ margin: 0 0 12px 0; }}
    .tip {{ color: #555; margin-bottom: 12px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; font-size: 13px; vertical-align: top; }}
    th {{ background: #f7f7f7; position: sticky; top: 0; }}
    tr:nth-child(even) {{ background: #fbfbfb; }}
    .mono {{ font-family: Consolas, monospace; }}
  </style>
</head>
<body>
  <h2>Feishu Inbound Events</h2>
  <div class=\"tip\">自动刷新: 5 秒 | limit={max(1, min(int(limit or 20), 100))} | JSON接口: /feishu/events</div>
  <table>
    <thead>
      <tr>
        <th>时间</th>
        <th>状态</th>
        <th>event_type</th>
        <th>message_type</th>
        <th>open_id</th>
        <th>用户消息</th>
        <th>错误</th>
      </tr>
    </thead>
    <tbody class=\"mono\">{table_body}</tbody>
  </table>
</body>
</html>
"""


if __name__ == "__main__":
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    if LOADED_ENV_PATH:
        logging.info("已加载环境变量文件: %s", LOADED_ENV_PATH)
    if REQUEST_PROXIES:
        logging.info(
            "检测到代理配置: http=%s, https=%s",
            REQUEST_PROXIES.get("http", ""),
            REQUEST_PROXIES.get("https", ""),
        )

    if FEISHU_VERIFY_ENABLED:
        logging.info("已启用飞书事件 token 校验(FEISHU_VERIFY_ENABLED=true)")
        logging.warning("当前脚本仅包含发送能力；如需接收飞书事件，请在 Web 服务入口调用 build_feishu_challenge_response/verify_feishu_event_token")

    validate_config()

    run_mode = os.getenv("RUN_MODE", "schedule").lower()
    # RUN_MODE=once: 立即执行一次；RUN_MODE=schedule: 启动定时任务；RUN_MODE=healthcheck: 执行预检；RUN_MODE=schedule: 启动 webhook 服务
    if run_mode == "once":
        run_daily_job()
        if SCOUT_ENABLED:
            try:
                from learning_scout import run_learning_scout_job

                run_learning_scout_job()
            except Exception as exc:
                logging.warning("once 模式执行 Learning Scout 失败: %s", exc)
        if DIGEST_ENABLED:
            try:
                run_digest_job()
            except Exception as exc:
                logging.warning("once 模式执行 Tech Digest 失败: %s", exc)
    elif run_mode == "healthcheck":
        raise SystemExit(run_health_check())
    elif run_mode == "server":
        uvicorn.run(app, host="0.0.0.0", port=8000)
    else:
        # 同时启动 Web 服务（手动触发）和调度器（定时任务）
        import threading

        def run_web():
            import uvicorn
            # Ensure root logger shows INFO even after uvicorn setup
            import logging
            logging.getLogger().setLevel(logging.INFO)
            uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

        web_thread = threading.Thread(target=run_web, daemon=True)
        web_thread.start()
        logging.info("Web 服务已启动（手动触发 /digest/run）")

        start_scheduler()