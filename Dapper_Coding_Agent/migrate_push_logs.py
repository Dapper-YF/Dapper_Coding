"""
数据库迁移脚本：创建 push_logs 表

用途：
  - 记录每次推送的 channel/target/source/status
  - 支持幂等性检查（idempotency_key）
  - 支持频率限制查询

运行方式：
  python migrate_push_logs.py

安全：使用 IF NOT EXISTS，可重复运行。
"""

import os
import sqlite3
import sys

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "dapper_coding.db"))


def migrate(db_path: str = DB_PATH) -> None:
    """创建 push_logs 表及相关索引"""
    print("数据库路径: %s" % db_path)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 1. 创建 push_logs 表
    cur.execute("""
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
    """)
    print("[OK] push_logs 表已就绪")

    # 2. 创建索引
    indexes = [
        ("idx_push_logs_user", "push_logs", "user_id"),
        ("idx_push_logs_idempotency", "push_logs", "idempotency_key"),
        ("idx_push_logs_created", "push_logs", "created_at"),
    ]
    for idx_name, table, col in indexes:
        cur.execute("CREATE INDEX IF NOT EXISTS %s ON %s(%s);" % (idx_name, table, col))
        print("[OK] 索引 %s 已就绪" % idx_name)

    conn.commit()

    # 3. 验证
    cur.execute("SELECT COUNT(*) FROM push_logs")
    count = cur.fetchone()[0]
    print("\n当前 push_logs 记录数: %d" % count)

    conn.close()
    print("\n迁移完成!")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else DB_PATH
    migrate(path)
