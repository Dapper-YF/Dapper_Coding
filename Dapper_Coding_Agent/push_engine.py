"""
统一推送引擎 - PushEngine

功能：
1. 统一三条推送通道（应用消息 / 群聊 / Webhook）
2. 幂等性：idempotency_key 防重复推送（24h 窗口）
3. 频率控制：同用户 1 分钟最多 3 条
4. 降级链：app 消息失败 → webhook 降级
5. 推送日志：push_logs 表记录每次推送

设计文档：WEBHOOK_PUSH_DESIGN.md
"""

import logging
import os
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)

# ============================================================
# 数据库路径
# ============================================================

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "dapper_coding.db"))

# ============================================================
# 时区
# ============================================================

TZ_CST = timezone(timedelta(hours=8))

def _now_cst() -> str:
    """返回 CST 时间字符串"""
    return datetime.now(TZ_CST).strftime("%Y-%m-%d %H:%M:%S")


# ============================================================
# push_logs 建表（幂等性 + 日志）
# ============================================================

_PUSH_LOGS_DDL = """
CREATE TABLE IF NOT EXISTS push_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    idempotency_key TEXT,
    user_id TEXT NOT NULL,
    channel TEXT NOT NULL,
    source TEXT DEFAULT '',
    msg_type TEXT NOT NULL,
    status TEXT NOT NULL,
    error TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now', '+8 hours'))
);
"""

_PUSH_LOGS_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_push_logs_user ON push_logs(user_id);",
    "CREATE INDEX IF NOT EXISTS idx_push_logs_idempotency ON push_logs(idempotency_key);",
    "CREATE INDEX IF NOT EXISTS idx_push_logs_created ON push_logs(created_at);",
]


# ============================================================
# PushEngine 类
# ============================================================

class PushEngine:
    """统一推送引擎

    使用方式：
        engine = PushEngine()
        result = engine.push(
            channel="app",
            target="user123",
            msg_type="markdown",
            content="## 今日课程...",
            source="daily_lesson",
            idempotency_key="lesson_user123_20260501",
        )
    """

    # 频率限制参数
    RATE_LIMIT_PER_MINUTE = 3        # 同用户 1 分钟最多 3 条
    RATE_LIMIT_WINDOW_SEC = 60       # 窗口：60 秒
    IDEMPOTENCY_WINDOW_HOURS = 24    # 幂等窗口：24 小时

    def __init__(self, db_path: str = ""):
        self.db_path = db_path or DB_PATH
        self._ensure_tables()
        # 延迟加载 WeiXinClient（避免循环导入）
        self._weixin_client = None
        self._webhook_url: str = os.getenv("WEIXIN_WEBHOOK_URL", "").strip()

    # ----------------------------------------------------------
    # 初始化
    # ----------------------------------------------------------

    def _ensure_tables(self) -> None:
        """确保 push_logs 表存在"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(_PUSH_LOGS_DDL)
                for idx_sql in _PUSH_LOGS_INDEXES:
                    conn.execute(idx_sql)
                conn.commit()
        except Exception as exc:
            logger.error("push_logs 建表失败: %s", exc)

    def _get_weixin_client(self):
        """延迟加载 WeiXinClient（避免循环导入）"""
        if self._weixin_client is None:
            try:
                from weixin_client import get_weixin_client
                self._weixin_client = get_weixin_client()
            except Exception as exc:
                logger.error("加载 WeiXinClient 失败: %s", exc)
                self._weixin_client = None
        return self._weixin_client

    # ----------------------------------------------------------
    # 公开接口：push()
    # ----------------------------------------------------------

    def push(
        self,
        channel: str,
        target: str,
        msg_type: str,
        content: str,
        *,
        title: str = "",
        url: str = "",
        picurl: str = "",
        priority: str = "normal",
        source: str = "",
        idempotency_key: str = "",
    ) -> Dict[str, Any]:
        """统一推送入口

        Args:
            channel: 推送通道 - app / chat / webhook
            target:  目标 - UserID / chatid
            msg_type: 消息类型 - text / markdown / news / textcard
            content:  消息正文
            title:    标题（textcard/news 必填）
            url:      链接（textcard/news 必填）
            picurl:   图片 URL（news 类型）
            priority: 优先级 - urgent / normal / low
            source:   来源标识
            idempotency_key: 幂等键（24h 防重复）

        Returns:
            {"ok": True, ...} 或 {"ok": False, "error": "..."}
        """
        # 1. 幂等检查
        if idempotency_key and self._is_duplicate(idempotency_key):
            logger.info("幂等命中，跳过推送: key=%s", idempotency_key)
            self._log_push(
                user_id=target,
                channel=channel,
                source=source,
                msg_type=msg_type,
                status="deduped",
                idempotency_key=idempotency_key,
            )
            return {"ok": True, "deduped": True, "channel": channel}

        # 2. 频率检查
        if not self._check_rate_limit(target):
            logger.warning("频率限制命中: target=%s", target)
            self._log_push(
                user_id=target,
                channel=channel,
                source=source,
                msg_type=msg_type,
                status="rate_limited",
                idempotency_key=idempotency_key,
            )
            return {"ok": False, "error": "rate_limited"}

        # 3. 执行推送（带降级）
        result = self._do_push_with_fallback(
            channel=channel,
            target=target,
            msg_type=msg_type,
            content=content,
            title=title,
            url=url,
            picurl=picurl,
        )

        # 4. 记录推送日志
        status = "success" if result.get("ok") else "failed"
        error = result.get("error", "")
        self._log_push(
            user_id=target,
            channel=channel,
            source=source,
            msg_type=msg_type,
            status=status,
            error=error,
            idempotency_key=idempotency_key,
        )

        return result

    # ----------------------------------------------------------
    # 幂等性检查
    # ----------------------------------------------------------

    def _is_duplicate(self, key: str) -> bool:
        """检查 24h 内是否有相同幂等键"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    """
                    SELECT 1 FROM push_logs
                    WHERE idempotency_key = ?
                      AND status IN ('success', 'deduped')
                      AND created_at > datetime('now', '-1 day', '+8 hours')
                    LIMIT 1
                    """,
                    (key,),
                ).fetchone()
                return row is not None
        except Exception as exc:
            logger.error("幂等检查失败: %s", exc)
            return False

    # ----------------------------------------------------------
    # 频率限制
    # ----------------------------------------------------------

    def _check_rate_limit(self, target: str) -> bool:
        """检查同用户 1 分钟内推送次数

        Returns:
            True = 允许推送，False = 超限
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    """
                    SELECT COUNT(*) FROM push_logs
                    WHERE user_id = ?
                      AND status = 'success'
                      AND created_at > datetime('now', '-60 seconds', '+8 hours')
                    """,
                    (target,),
                ).fetchone()
                count = row[0] if row else 0
                return count < self.RATE_LIMIT_PER_MINUTE
        except Exception as exc:
            logger.error("频率检查失败: %s", exc)
            return True  # 检查失败时放行

    # ----------------------------------------------------------
    # 推送执行（含降级链）
    # ----------------------------------------------------------

    def _do_push_with_fallback(
        self,
        channel: str,
        target: str,
        msg_type: str,
        content: str,
        title: str = "",
        url: str = "",
        picurl: str = "",
    ) -> Dict[str, Any]:
        """执行推送，失败时自动降级

        降级链：
        - app 发送失败 → 尝试 webhook（如有配置）
        - webhook 发送失败 → 记录失败
        - chat 发送失败 → 不降级（群聊无降级路径）
        """
        # 主通道推送
        result = self._do_push(channel, target, msg_type, content, title, url, picurl)

        if result.get("ok"):
            return result

        # 降级：app → webhook（仅 app 通道降级）
        if channel == "app" and self._webhook_url:
            logger.info("app 推送失败，降级到 webhook: target=%s", target)
            fallback = self._do_push("webhook", target, msg_type, content, title, url, picurl)
            if fallback.get("ok"):
                fallback["degraded_from"] = "app"
                return fallback

        return result

    def _do_push(
        self,
        channel: str,
        target: str,
        msg_type: str,
        content: str,
        title: str = "",
        url: str = "",
        picurl: str = "",
    ) -> Dict[str, Any]:
        """根据通道分发到具体发送逻辑"""
        if channel == "app":
            return self._push_app(target, msg_type, content, title, url, picurl)
        elif channel == "chat":
            return self._push_chat(target, msg_type, content, title, url, picurl)
        elif channel == "webhook":
            return self._push_webhook(content, title, url)
        else:
            return {"ok": False, "error": f"unknown channel: {channel}"}

    # ----------------------------------------------------------
    # 通道实现
    # ----------------------------------------------------------

    def _push_app(
        self,
        target: str,
        msg_type: str,
        content: str,
        title: str = "",
        url: str = "",
        picurl: str = "",
    ) -> Dict[str, Any]:
        """应用消息推送（通过 WeiXinClient）"""
        client = self._get_weixin_client()
        if not client:
            return {"ok": False, "error": "weixin_client_unavailable"}

        try:
            success = False
            if msg_type == "text":
                success = client.send_text(content, to_user=target)
            elif msg_type == "markdown":
                success = client.send_markdown(content, to_user=target)
            elif msg_type == "textcard":
                if not title or not url:
                    return {"ok": False, "error": "textcard requires title and url"}
                success = client.send_textcard(title, content, url, to_user=target)
            elif msg_type == "news":
                from weixin_client import WeiXinArticle
                article = WeiXinArticle(
                    title=title or "消息",
                    description=content[:100] if content else "",
                    url=url or "",
                    picurl=picurl or "",
                )
                success = client.send_news([article], to_user=target)
            else:
                return {"ok": False, "error": f"unsupported msg_type for app: {msg_type}"}

            if success:
                return {"ok": True, "channel": "app", "sent_at": _now_cst()}
            else:
                return {"ok": False, "error": "send_failed"}

        except Exception as exc:
            logger.error("app 推送异常: %s", exc)
            return {"ok": False, "error": str(exc)}

    def _push_chat(
        self,
        target: str,
        msg_type: str,
        content: str,
        title: str = "",
        url: str = "",
        picurl: str = "",
    ) -> Dict[str, Any]:
        """群聊消息推送（通过 WeiXinClient）"""
        client = self._get_weixin_client()
        if not client:
            return {"ok": False, "error": "weixin_client_unavailable"}

        try:
            success = False
            if msg_type == "text":
                success = client.send_text_to_chat(content, chat_id=target)
            elif msg_type == "markdown":
                success = client.send_markdown_to_chat(content, chat_id=target)
            else:
                return {"ok": False, "error": f"unsupported msg_type for chat: {msg_type}"}

            if success:
                return {"ok": True, "channel": "chat", "sent_at": _now_cst()}
            else:
                return {"ok": False, "error": "send_failed"}

        except Exception as exc:
            logger.error("chat 推送异常: %s", exc)
            return {"ok": False, "error": str(exc)}

    def _push_webhook(
        self,
        content: str,
        title: str = "",
        url: str = "",
    ) -> Dict[str, Any]:
        """Webhook 群机器人推送"""
        if not self._webhook_url:
            return {"ok": False, "error": "webhook_url_not_configured"}

        try:
            # 分段处理（企业微信限制单条 2000 字）
            max_len = 2000
            if len(content) > max_len:
                parts = [content[i : i + max_len] for i in range(0, len(content), max_len)]
                for part in parts:
                    payload = {
                        "msgtype": "text",
                        "text": {"content": part, "mentioned_list": []},
                    }
                    resp = requests.post(self._webhook_url, json=payload, timeout=10)
                    if resp.status_code != 200:
                        return {"ok": False, "error": f"webhook_http_{resp.status_code}"}
                    time.sleep(0.5)
            else:
                payload = {
                    "msgtype": "text",
                    "text": {"content": content, "mentioned_list": []},
                }
                resp = requests.post(self._webhook_url, json=payload, timeout=10)
                if resp.status_code != 200:
                    return {"ok": False, "error": f"webhook_http_{resp.status_code}"}

            return {"ok": True, "channel": "webhook", "sent_at": _now_cst()}

        except Exception as exc:
            logger.error("webhook 推送异常: %s", exc)
            return {"ok": False, "error": str(exc)}

    # ----------------------------------------------------------
    # 推送日志
    # ----------------------------------------------------------

    def _log_push(
        self,
        user_id: str,
        channel: str,
        source: str,
        msg_type: str,
        status: str,
        error: str = "",
        idempotency_key: str = "",
    ) -> None:
        """写入推送日志"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO push_logs
                        (idempotency_key, user_id, channel, source, msg_type, status, error, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        idempotency_key or None,
                        user_id,
                        channel,
                        source,
                        msg_type,
                        status,
                        error,
                        _now_cst(),
                    ),
                )
                conn.commit()
        except Exception as exc:
            logger.error("推送日志写入失败: %s", exc)

    # ----------------------------------------------------------
    # 查询接口（供外部使用）
    # ----------------------------------------------------------

    def get_push_history(
        self,
        user_id: str,
        limit: int = 20,
    ) -> list:
        """查询用户推送历史"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    """
                    SELECT * FROM push_logs
                    WHERE user_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (user_id, limit),
                ).fetchall()
                return [dict(r) for r in rows]
        except Exception as exc:
            logger.error("查询推送历史失败: %s", exc)
            return []

    def get_push_stats(self, user_id: str) -> Dict[str, Any]:
        """查询用户推送统计（最近 24h）"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    """
                    SELECT
                        COUNT(*) as total,
                        SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) as success,
                        SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) as failed,
                        SUM(CASE WHEN status='deduped' THEN 1 ELSE 0 END) as deduped,
                        SUM(CASE WHEN status='rate_limited' THEN 1 ELSE 0 END) as rate_limited
                    FROM push_logs
                    WHERE user_id = ?
                      AND created_at > datetime('now', '-1 day', '+8 hours')
                    """,
                    (user_id,),
                ).fetchone()
                return {
                    "total": row[0] or 0,
                    "success": row[1] or 0,
                    "failed": row[2] or 0,
                    "deduped": row[3] or 0,
                    "rate_limited": row[4] or 0,
                }
        except Exception as exc:
            logger.error("查询推送统计失败: %s", exc)
            return {"total": 0, "success": 0, "failed": 0, "deduped": 0, "rate_limited": 0}


# ============================================================
# 便捷函数（供外部直接调用）
# ============================================================

def push_message(
    channel: str,
    target: str,
    msg_type: str,
    content: str,
    **kwargs,
) -> Dict[str, Any]:
    """便捷推送函数（每次创建新引擎实例）

    适合一次性推送场景；高频场景建议复用 PushEngine 实例。
    """
    engine = PushEngine()
    return engine.push(channel, target, msg_type, content, **kwargs)
