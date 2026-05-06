# -*- coding: utf-8 -*-
"""
对话管理器 - 短期记忆（会话管理）
管理多轮对话上下文
"""

import sqlite3
import os
from typing import List, Optional, Tuple
from datetime import datetime, timedelta

# 复用现有的 DB_PATH 逻辑
def get_project_root():
    """获取项目根目录，兼容本地和云端"""
    # 优先从环境变量读取
    project_root = os.getenv('PROJECT_ROOT', '')
    if project_root:
        return project_root
    
    # 尝试从当前文件位置推断
    current_file = os.path.dirname(os.path.abspath(__file__))
    # 向上两级找到项目根目录
    if os.path.basename(current_file) == 'Dapper_Coding':
        return current_file
    
    # 兼容旧路径
    legacy_path = '/opt/Dapper_Coding_Agent'
    if os.path.exists(legacy_path):
        return legacy_path
    
    # 默认返回当前目录
    return os.getcwd()

def get_db_path():
    """获取数据库路径"""
    return os.path.join(get_project_root(), 'dapper_memory.db')

# 延迟初始化 DB_PATH
_db_path = None

def get_db_path_lazy():
    """延迟获取 DB_PATH（避免模块加载时出错）"""
    global _db_path
    if _db_path is None:
        _db_path = get_db_path()
    return _db_path


class DialogueManager:
    """对话管理器"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or get_db_path_lazy()
        self._ensure_tables()
    
    def _ensure_tables(self):
        """确保对话表存在"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS dialogue_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, channel)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS dialogue_turns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES dialogue_sessions(id)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_turns_session
                ON dialogue_turns(session_id, created_at DESC)
            """)
            # 迁移：添加 title 列
            try:
                conn.execute("ALTER TABLE dialogue_sessions ADD COLUMN title TEXT DEFAULT ''")
            except sqlite3.OperationalError:
                pass

            # 迁移：添加 client_session_id 列，移除 UNIQUE(user_id, channel)
            # 使同一个用户可以拥有多个会话（每个 Android 会话用一个 UUID 标识）
            try:
                conn.execute("SELECT client_session_id FROM dialogue_sessions LIMIT 1")
            except sqlite3.OperationalError:
                # 需要重建表以移除 UNIQUE 约束
                conn.execute("ALTER TABLE dialogue_sessions RENAME TO dialogue_sessions_old")
                conn.execute("""
                    CREATE TABLE dialogue_sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        channel TEXT NOT NULL,
                        client_session_id TEXT DEFAULT '',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        title TEXT DEFAULT ''
                    )
                """)
                # 复制现有数据
                try:
                    conn.execute("""
                        INSERT INTO dialogue_sessions (id, user_id, channel, created_at, last_active, title)
                        SELECT id, user_id, channel, created_at, last_active, title
                        FROM dialogue_sessions_old
                    """)
                except sqlite3.OperationalError:
                    # 如果旧表没有 title 列
                    conn.execute("""
                        INSERT INTO dialogue_sessions (id, user_id, channel, created_at, last_active)
                        SELECT id, user_id, channel, created_at, last_active
                        FROM dialogue_sessions_old
                    """)
                conn.execute("DROP TABLE dialogue_sessions_old")
                conn.commit()

            conn.commit()
    
    def get_or_create_session(self, user_id: str, channel: str) -> int:
        """获取或创建会话（无 client_session_id 的旧调用方式）"""
        return self.get_or_create_session_by_client_id(user_id, channel, "")

    def get_or_create_session_by_client_id(self, user_id: str, channel: str, client_session_id: str) -> int:
        """获取或创建会话（根据 client_session_id 区分不同 Android 会话）"""
        with sqlite3.connect(self.db_path) as conn:
            # 查找匹配 client_session_id 的现有会话
            if client_session_id:
                row = conn.execute(
                    "SELECT id FROM dialogue_sessions WHERE user_id=? AND channel=? AND client_session_id=?",
                    (user_id, channel, client_session_id)
                ).fetchone()
                if row:
                    conn.execute(
                        "UPDATE dialogue_sessions SET last_active=CURRENT_TIMESTAMP WHERE id=?",
                        (row[0],)
                    )
                    conn.commit()
                    return row[0]

            # 对于没有 client_session_id 的情况，查找最近会话（向后兼容）
            if not client_session_id:
                row = conn.execute(
                    "SELECT id FROM dialogue_sessions WHERE user_id=? AND channel=? AND client_session_id='' ORDER BY last_active DESC LIMIT 1",
                    (user_id, channel)
                ).fetchone()
                if row:
                    conn.execute(
                        "UPDATE dialogue_sessions SET last_active=CURRENT_TIMESTAMP WHERE id=?",
                        (row[0],)
                    )
                    conn.commit()
                    return row[0]

            # 创建新会话
            cursor = conn.execute(
                "INSERT INTO dialogue_sessions (user_id, channel, client_session_id) VALUES (?, ?, ?)",
                (user_id, channel, client_session_id)
            )
            conn.commit()
            return cursor.lastrowid
    
    def add_turn(self, session_id: int, role: str, content: str):
        """添加对话轮次"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO dialogue_turns (session_id, role, content) VALUES (?, ?, ?)",
                (session_id, role, content)
            )
            conn.execute(
                "UPDATE dialogue_sessions SET last_active=CURRENT_TIMESTAMP WHERE id=?",
                (session_id,)
            )
            conn.commit()
    
    def get_recent_turns(self, session_id: int, limit: int = 10) -> List[Tuple[str, str]]:
        """获取最近的对话轮次"""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT role, content 
                FROM dialogue_turns 
                WHERE session_id=? 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (session_id, limit)).fetchall()
            # 反转，最早的在前
            return list(reversed(rows))
    
    def build_context(self, user_id: str, channel: str, limit: int = 10, client_session_id: str = "") -> str:
        """构建对话上下文（用于 LLM）"""
        session_id = self.get_or_create_session_by_client_id(user_id, channel, client_session_id)
        turns = self.get_recent_turns(session_id, limit)
        
        if not turns:
            return ""
        
        context_parts = []
        for role, content in turns:
            role_name = "用户" if role == "user" else "助手"
            context_parts.append(f"{role_name}：{content}")
        
        return "\n".join(context_parts)
    
    def cleanup_old_sessions(self, hours: int = 24):
        """清理超时会话"""
        with sqlite3.connect(self.db_path) as conn:
            # 查找超时会话
            threshold = (datetime.now() - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
            old_sessions = conn.execute(
                "SELECT id FROM dialogue_sessions WHERE last_active < ?",
                (threshold,)
            ).fetchall()
            
            for (session_id,) in old_sessions:
                conn.execute("DELETE FROM dialogue_turns WHERE session_id=?", (session_id,))
                conn.execute("DELETE FROM dialogue_sessions WHERE id=?", (session_id,))
            
            conn.commit()
            return len(old_sessions)
    
    def add_user_message(self, user_id: str, channel: str, message: str, client_session_id: str = ""):
        """添加用户消息"""
        session_id = self.get_or_create_session_by_client_id(user_id, channel, client_session_id)
        self.add_turn(session_id, "user", message)

    def add_assistant_message(self, user_id: str, channel: str, message: str, client_session_id: str = ""):
        """添加助手消息"""
        session_id = self.get_or_create_session_by_client_id(user_id, channel, client_session_id)
        self.add_turn(session_id, "assistant", message)

    def message_count(self, user_id: str, channel: str, client_session_id: str = "") -> int:
        """获取会话消息总数（用于判断是否为首次对话）"""
        session_id = self.get_or_create_session_by_client_id(user_id, channel, client_session_id)
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM dialogue_turns WHERE session_id=?",
                (session_id,)
            ).fetchone()
            return row[0] if row else 0

    def set_title(self, user_id: str, channel: str, title: str, client_session_id: str = ""):
        """设置会话标题"""
        session_id = self.get_or_create_session_by_client_id(user_id, channel, client_session_id)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE dialogue_sessions SET title=? WHERE id=?",
                (title, session_id)
            )
            conn.commit()

    def get_title(self, user_id: str, channel: str, client_session_id: str = "") -> str:
        """获取会话标题"""
        session_id = self.get_or_create_session_by_client_id(user_id, channel, client_session_id)
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT title FROM dialogue_sessions WHERE id=?",
                (session_id,)
            ).fetchone()
            return (row[0] if row and row[0] else "") if row else ""


# 全局实例
_dialogue_manager: Optional[DialogueManager] = None


def get_dialogue_manager() -> DialogueManager:
    """获取对话管理器实例"""
    global _dialogue_manager
    if _dialogue_manager is None:
        _dialogue_manager = DialogueManager()
    return _dialogue_manager
