"""
Learning Scout v2 - 统一记忆层 (Unified Memory)
=================================================

提供智能体的记忆能力：
- 用户画像管理
- 学习进度追踪
- 阅读历史记录
- Tech Digest 推送历史
"""

import json
import logging
import os
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

# ============================================================
# 配置
# ============================================================

def resolve_env_file(env_file: str = ".env") -> str:
    override = os.getenv("DAPPER_ENV_FILE", "").strip()
    if override:
        return os.path.abspath(override)
    if os.path.isabs(env_file):
        return env_file
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, env_file)


def load_local_env(env_file: str = ".env") -> Optional[str]:
    """加载 .env 环境变量（与 learning_scout.py 保持一致）"""
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
        logging.warning("memory.py 读取 .env 失败: %s", exc)
    return resolved


# 确保 .env 加载
try:
    load_local_env()
except Exception:
    pass

DB_PATH = resolve_env_file("dapper_memory.db")

# ============================================================
# 数据模型
# ============================================================

@dataclass
class UserProfile:
    """用户画像"""
    user_id: str
    关注领域: str = ""  # 逗号分隔: "NLP,CV,ML"
    难度偏好: str = "入门"  # 入门 / 进阶 / 高级
    阅读深度偏好: str = "中等"  # 简短 / 中等 / 详细
    热度权重: str = "{}"  # JSON: {"NLP": 0.8, "CV": 0.5}
    weixin_webhook: str = ""  # 企业微信 Webhook URL（可选，覆盖全局配置）
    digest_enabled: bool = True  # 是否启用 Digest 推送
    created_at: str = ""
    updated_at: str = ""

    def get_热度权重_dict(self) -> Dict[str, float]:
        try:
            return json.loads(self.热度权重)
        except Exception:
            return {}

    def set_热度权重_dict(self, d: Dict[str, float]):
        self.热度权重 = json.dumps(d, ensure_ascii=False)

    def get_关注领域_list(self) -> List[str]:
        if not self.关注领域:
            return []
        return [x.strip() for x in self.关注领域.split(",") if x.strip()]


@dataclass
class LearningProgress:
    """学习进度"""
    user_id: str
    direction: str = ""
    total_days: int = 56
    current_day: int = 1
    stage_summary: str = ""
    started_at: str = ""


@dataclass
class ReadingRecord:
    """阅读记录"""
    id: int
    user_id: str
    item_id: int
    action: str  # click / ignore / feedback
    feedback_text: Optional[str]
    created_at: str


@dataclass
class DigestRecord:
    """Tech Digest 推送记录"""
    id: int
    user_id: str
    push_date: str
    title: str
    content: str
    source_articles: str  # JSON 数组
    created_at: str


# ============================================================
# 数据库初始化
# ============================================================

def init_memory_db() -> None:
    """初始化记忆层所需的数据库表"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            # user_profiles: 用户画像
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id TEXT PRIMARY KEY,
            
            # 补充新列（如果不存在）- 教学智能体需要的字段
            try:
                conn.execute("ALTER TABLE user_profiles ADD COLUMN learning_level TEXT DEFAULT 'intermediate'")
            except sqlite3.OperationalError:
                pass  # 列已存在
            
            try:
                conn.execute("ALTER TABLE user_profiles ADD COLUMN interests TEXT DEFAULT '[]'")
            except sqlite3.OperationalError:
                pass  # 列已存在
            
            try:
                conn.execute("ALTER TABLE user_profiles ADD COLUMN learning_history TEXT DEFAULT '[]'")
            except sqlite3.OperationalError:
                pass  # 列已存在

                    关注领域 TEXT DEFAULT '',
                    难度偏好 TEXT DEFAULT '入门',
                    阅读深度偏好 TEXT DEFAULT '中等',
                    热度权重 TEXT DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # digest_history: Tech Digest 推送记录
            conn.execute("""
                CREATE TABLE IF NOT EXISTS digest_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    push_date TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source_articles TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(user_id, push_date)
                )
            """)

            # reading_history: 阅读历史（增强版）
            conn.execute("""
                CREATE TABLE IF NOT EXISTS reading_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    item_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    feedback_text TEXT,
                    created_at TEXT NOT NULL
                )
            """)


            # 迁移：为已存在的表添加新列
            try:
                cursor = conn.execute("PRAGMA table_info(user_profiles)")
                existing_cols = {row[1] for row in cursor.fetchall()}
                if "weixin_webhook" not in existing_cols:
                    conn.execute("ALTER TABLE user_profiles ADD COLUMN weixin_webhook TEXT DEFAULT ''")
                if "digest_enabled" not in existing_cols:
                    conn.execute("ALTER TABLE user_profiles ADD COLUMN digest_enabled INTEGER DEFAULT 1")
                conn.commit()
                logging.info("Migration: user_profiles 表已补充新列")
            except Exception as exc:
                logging.warning("Migration 失败: %s", exc)
            conn.commit()
        logging.info("记忆层数据库初始化完成")
    except Exception as exc:
        logging.error("记忆层数据库初始化失败: %s", exc)
        raise


# ============================================================
# 用户画像操作
# ============================================================

def get_profile(user_id: str) -> UserProfile:
    """获取用户画像，不存在则创建默认记录"""
    if not user_id:
        return UserProfile(user_id="", created_at=_now(), updated_at=_now())

    try:
        init_memory_db()
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM user_profiles WHERE user_id = ?",
                (user_id,)
            ).fetchone()

            if row:
                row = dict(row)  # sqlite3.Row has no .get(), convert to dict
                digest_enabled_val = row.get("digest_enabled", 1)
                if isinstance(digest_enabled_val, int):
                    digest_enabled_val = bool(digest_enabled_val)
                return UserProfile(
                    user_id=row["user_id"],
                    关注领域=row.get("关注领域") or "",
                    难度偏好=row.get("难度偏好") or "入门",
                    阅读深度偏好=row.get("阅读深度偏好") or "中等",
                    热度权重=row.get("热度权重") or "{}",
                    weixin_webhook=row.get("weixin_webhook") or "",
                    digest_enabled=digest_enabled_val,
                    created_at=row.get("created_at") or _now(),
                    updated_at=row.get("updated_at") or _now(),
                )

            # 不存在则创建默认记录
            now = _now()
            conn.execute(
                """INSERT INTO user_profiles(user_id, created_at, updated_at)
                   VALUES (?, ?, ?)""",
                (user_id, now, now)
            )
            conn.commit()
            return UserProfile(user_id=user_id, created_at=now, updated_at=now)

    except Exception as exc:
        logging.warning("get_profile 失败(user_id=%s): %s", user_id, exc)
        return UserProfile(user_id=user_id, created_at=_now(), updated_at=_now())


def update_profile(user_id: str, **fields) -> None:
    """更新用户画像字段"""
    if not user_id:
        return

    allowed_fields = {"关注领域", "难度偏好", "阅读深度偏好", "热度权重", "weixin_webhook", "digest_enabled"}
    payload = {k: v for k, v in fields.items() if k in allowed_fields}

    if not payload:
        return

    try:
        init_memory_db()
        now = _now()
        with sqlite3.connect(DB_PATH) as conn:
            # 确保记录存在
            conn.execute(
                "INSERT OR IGNORE INTO user_profiles(user_id, created_at, updated_at) VALUES (?, ?, ?)",
                (user_id, now, now)
            )
            # 更新字段
            for key, value in payload.items():
                conn.execute(
                    "UPDATE user_profiles SET {} = ?, updated_at = ? WHERE user_id = ?".format(key),
                    (value, now, user_id)
                )
            conn.commit()
        logging.info("update_profile 完成(user_id=%s): %s", user_id, list(payload.keys()))
    except Exception as exc:
        logging.warning("update_profile 失败(user_id=%s): %s", user_id, exc)


def update_热度权重(user_id: str, 领域: str, delta: float) -> None:
    """根据反馈更新领域热度权重"""
    profile = get_profile(user_id)
    weights = profile.get_热度权重_dict()

    current = weights.get(领域, 0.5)
    new_weight = max(0.0, min(1.0, current + delta))
    weights[领域] = new_weight

    update_profile(user_id, 热度权重=json.dumps(weights, ensure_ascii=False))


# ============================================================
# 学习进度操作
# ============================================================

def get_learning_progress(user_id: str) -> Optional[LearningProgress]:
    """获取学习进度"""
    if not user_id:
        return None

    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM learning_progress WHERE user_id = ?",
                (user_id,)
            ).fetchone()

            if row:
                return LearningProgress(
                    user_id=row["user_id"],
                    direction=row["direction"] or "",
                    total_days=row["total_days"] or 56,
                    current_day=row["current_day"] or 1,
                    stage_summary=row["stage_summary"] or "",
                    started_at=row["started_at"] or "",
                )
    except Exception as exc:
        logging.warning("get_learning_progress 失败(user_id=%s): %s", user_id, exc)

    return None


def update_learning_progress(user_id: str, **fields) -> None:
    """更新学习进度"""
    if not user_id:
        return

    allowed = {"current_day", "direction", "total_days", "stage_summary"}
    payload = {k: v for k, v in fields.items() if k in allowed}

    if not payload:
        return

    try:
        now = _now()
        with sqlite3.connect(DB_PATH) as conn:
            # 确保记录存在
            conn.execute(
                """INSERT OR IGNORE INTO learning_progress(user_id, started_at)
                   VALUES (?, ?)""",
                (user_id, now)
            )
            for key, value in payload.items():
                conn.execute(
                    "UPDATE learning_progress SET {} = ? WHERE user_id = ?".format(key),
                    (value, user_id)
                )
            conn.commit()
    except Exception as exc:
        logging.warning("update_learning_progress 失败: %s", exc)


def advance_learning_day(user_id: str) -> int:
    """推进学习进度到下一天，返回新的 current_day"""
    progress = get_learning_progress(user_id)
    if not progress:
        return 1

    new_day = min(progress.current_day + 1, progress.total_days)
    update_learning_progress(user_id, current_day=new_day)
    return new_day


# ============================================================
# 阅读历史操作
# ============================================================

def record_reading(
    user_id: str,
    item_id: int,
    action: str,
    feedback_text: Optional[str] = None
) -> None:
    """记录用户阅读行为"""
    if not user_id or action not in {"click", "ignore", "feedback"}:
        return

    try:
        init_memory_db()
        now = _now()
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """INSERT INTO reading_history(user_id, item_id, action, feedback_text, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (user_id, item_id, action, feedback_text, now)
            )
            conn.commit()
        logging.info("record_reading: user=%s item=%s action=%s", user_id, item_id, action)
    except Exception as exc:
        logging.warning("record_reading 失败: %s", exc)


def get_reading_history(user_id: str, days: int = 7) -> List[ReadingRecord]:
    """获取用户最近 N 天的阅读历史"""
    if not user_id:
        return []

    try:
        init_memory_db()
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """SELECT * FROM reading_history
                   WHERE user_id = ? AND created_at >= ?
                   ORDER BY created_at DESC""",
                (user_id, cutoff)
            ).fetchall()

            return [
                ReadingRecord(
                    id=row["id"],
                    user_id=row["user_id"],
                    item_id=row["item_id"],
                    action=row["action"],
                    feedback_text=row["feedback_text"],
                    created_at=row["created_at"],
                )
                for row in rows
            ]
    except Exception as exc:
        logging.warning("get_reading_history 失败: %s", exc)
        return []


def get_user_clicked_items(user_id: str, days: int = 30) -> List[int]:
    """获取用户点击过的文章 ID 列表（用于去重）"""
    if not user_id:
        return []

    try:
        init_memory_db()
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        with sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute(
                """SELECT DISTINCT item_id FROM reading_history
                   WHERE user_id = ? AND action = 'click' AND created_at >= ?""",
                (user_id, cutoff)
            ).fetchall()
            return [row[0] for row in rows]
    except Exception as exc:
        logging.warning("get_user_clicked_items 失败: %s", exc)
        return []


# ============================================================
# Digest History 操作
# ============================================================

def record_digest(
    user_id: str,
    push_date: str,
    title: str,
    content: str,
    source_articles: List[Dict[str, Any]]
) -> None:
    """记录 Tech Digest 推送"""
    if not user_id:
        return

    try:
        init_memory_db()
        now = _now()
        articles_json = json.dumps(source_articles, ensure_ascii=False)
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO digest_history
                   (user_id, push_date, title, content, source_articles, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (user_id, push_date, title, content, articles_json, now)
            )
            conn.commit()
        logging.info("record_digest: user=%s date=%s title=%s", user_id, push_date, title[:30])
    except Exception as exc:
        logging.warning("record_digest 失败: %s", exc)


def get_latest_digest(user_id: str) -> Optional[DigestRecord]:
    """获取用户最近一次 Digest 推送"""
    if not user_id:
        return None

    try:
        init_memory_db()
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """SELECT * FROM digest_history
                   WHERE user_id = ?
                   ORDER BY push_date DESC LIMIT 1""",
                (user_id,)
            ).fetchone()

            if row:
                return DigestRecord(
                    id=row["id"],
                    user_id=row["user_id"],
                    push_date=row["push_date"],
                    title=row["title"],
                    content=row["content"],
                    source_articles=row["source_articles"],
                    created_at=row["created_at"],
                )
    except Exception as exc:
        logging.warning("get_latest_digest 失败: %s", exc)

    return None


# ============================================================
# 工具函数
# ============================================================

def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_all_active_users() -> List[str]:
    """获取所有启用 Digest 的用户 ID"""
    try:
        init_memory_db()
        with sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute(
                "SELECT user_id FROM user_profiles WHERE digest_enabled = 1"
            ).fetchall()
            result = [row[0] for row in rows if row[0]]
            logging.info("get_all_active_users: found %s users with digest_enabled=1", len(result))
            return result
    except Exception as exc:
        logging.warning("get_all_active_users 失败: %s", exc)
        return []


def register_user(
    user_id: str,
    关注领域: str = "",
    难度偏好: str = "入门",
    weixin_webhook: str = "",
) -> None:
    """注册新用户或更新已有用户配置"""
    if not user_id:
        return
    
    try:
        init_memory_db()
        now = _now()
        with sqlite3.connect(DB_PATH) as conn:
            # 检查是否已存在
            existing = conn.execute(
                "SELECT user_id FROM user_profiles WHERE user_id = ?",
                (user_id,)
            ).fetchone()
            
            if existing:
                # 更新
                conn.execute(
                    """UPDATE user_profiles SET 
                       关注领域 = ?, 难度偏好 = ?, weixin_webhook = ?, updated_at = ?
                       WHERE user_id = ?""",
                    (关注领域, 难度偏好, weixin_webhook, now, user_id)
                )
                logging.info("register_user: updated user %s", user_id)
            else:
                # 新增
                conn.execute(
                    """INSERT INTO user_profiles 
                       (user_id, 关注领域, 难度偏好, weixin_webhook, digest_enabled, created_at, updated_at)
                       VALUES (?, ?, ?, ?, 1, ?, ?)""",
                    (user_id, 关注领域, 难度偏好, weixin_webhook, now, now)
                )
                logging.info("register_user: created new user %s", user_id)
            conn.commit()
    except Exception as exc:
        logging.warning("register_user 失败(user_id=%s): %s", user_id, exc)


def set_digest_enabled(user_id: str, enabled: bool) -> None:
    """启用/禁用用户的 Digest 推送"""
    if not user_id:
        return
    
    try:
        init_memory_db()
        now = _now()
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "UPDATE user_profiles SET digest_enabled = ?, updated_at = ? WHERE user_id = ?",
                (1 if enabled else 0, now, user_id)
            )
            conn.commit()
        logging.info("set_digest_enabled: user=%s enabled=%s", user_id, enabled)
    except Exception as exc:
        logging.warning("set_digest_enabled 失败: %s", exc)


# ============================================================
# 自我测试
# ============================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    print("=" * 50)
    print("Learning Scout v2 - Memory Layer Test")
    print("=" * 50)

    # 初始化数据库
    init_memory_db()

    # 测试用户 ID
    test_user = "test_user_001"

    # 1. 测试用户画像
    print("\n[1] 测试用户画像...")
    profile = get_profile(test_user)
    print(f"    初始画像: {profile}")

    update_profile(test_user, 关注领域="NLP,CV", 难度偏好="入门")
    profile = get_profile(test_user)
    print(f"    更新后: 关注领域={profile.关注领域}, 难度={profile.难度偏好}")

    # 2. 测试热度权重更新
    print("\n[2] 测试热度权重...")
    update_热度权重(test_user, "NLP", 0.2)
    update_热度权重(test_user, "CV", -0.1)
    profile = get_profile(test_user)
    print(f"    NLP={profile.get_热度权重_dict().get('NLP', 0)}, CV={profile.get_热度权重_dict().get('CV', 0)}")

    # 3. 测试阅读记录
    print("\n[3] 测试阅读记录...")
    record_reading(test_user, 1, "click")
    record_reading(test_user, 2, "ignore")
    history = get_reading_history(test_user)
    print(f"    历史记录数: {len(history)}")

    clicked = get_user_clicked_items(test_user)
    print(f"    点击过的文章: {clicked}")

    # 4. 测试 Digest 记录
    print("\n[4] 测试 Digest 记录...")
    record_digest(test_user, "2026-04-26", "今日 AI 速报", "测试内容...", [{"title": "测试", "url": "http://test.com"}])
    latest = get_latest_digest(test_user)
    print(f"    最新 Digest: {latest.title if latest else 'None'}")

    # 5. 测试活跃用户
    print("\n[5] 测试活跃用户...")
    users = get_all_active_users()
    print(f"    活跃用户数: {len(users)}")

    print("\n" + "=" * 50)
    print("Memory Layer Test PASSED ✓")
    print("=" * 50)


# ============================================================
# 用户兴趣更新（反思机制）
# ============================================================

def update_user_interests(user_id: str, topic: str) -> bool:
    """更新用户感兴趣的话题"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            row = conn.execute(
                "SELECT interests FROM user_profiles WHERE user_id=?",
                (user_id,)
            ).fetchone()
            
            if not row:
                return False
            
            try:
                interests = json.loads(row[0]) if row[0] else []
            except json.JSONDecodeError:
                interests = []
            
            # 提取关键词（简化版）
            keywords = extract_keywords_from_topic(topic)
            for kw in keywords:
                if kw not in interests:
                    interests.append(kw)
            
            interests = interests[-50:]
            
            conn.execute(
                "UPDATE user_profiles SET interests=? WHERE user_id=?",
                (json.dumps(interests, ensure_ascii=False), user_id)
            )
            conn.commit()
            return True
            
    except Exception as exc:
        logging.error("update_user_interests failed: %s", exc)
        return False


def extract_keywords_from_topic(topic: str) -> list:
    """从话题中提取关键词"""
    import re
    cleaned = re.sub(r'[^\w\s]', ' ', topic.lower())
    words = cleaned.split()
    
    tech_keywords = [
        'python', 'javascript', 'java', 'rust', 'go', 'typescript',
        'machine-learning', 'deep-learning', 'nlp', 'cv', 'ai', 'ml', 'dl',
        'web', 'frontend', 'backend', 'api', 'database',
        'docker', 'kubernetes', 'git', 'linux',
        'react', 'vue', 'nodejs', 'flask', 'django',
        'tensorflow', 'pytorch', 'pandas', 'numpy',
    ]
    
    keywords = []
    for word in words:
        for kw in tech_keywords:
            if kw in word or word in kw:
                keywords.append(kw)
    
    return list(dict.fromkeys(keywords))[:10]
