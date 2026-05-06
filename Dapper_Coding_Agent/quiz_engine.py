# -*- coding: utf-8 -*-
"""
Phase 14: 知识掌握检测引擎
单题出题 + 评判 + mastery_score 更新
"""

import json
import logging
import re
import sqlite3
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

DB_PATH = "/opt/Dapper_Coding_Agent/dapper_memory.db"


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---- 建表 ----
def init_quiz_db():
    """确保两张新表存在"""
    sql = """
    CREATE TABLE IF NOT EXISTS lesson_assessments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        lesson_id INTEGER NOT NULL,
        question TEXT NOT NULL,
        question_type TEXT NOT NULL,
        correct_answer TEXT NOT NULL,
        options TEXT,
        user_answer TEXT,
        is_correct INTEGER,
        created_at TEXT DEFAULT (datetime('now', '+8 hours')),
        answered_at TEXT,
        FOREIGN KEY (lesson_id) REFERENCES generated_lessons(id)
    );
    CREATE TABLE IF NOT EXISTS mastery_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        topic TEXT NOT NULL,
        lesson_id INTEGER,
        mastery_score REAL DEFAULT 0.5,
        total_attempts INTEGER DEFAULT 0,
        correct_attempts INTEGER DEFAULT 0,
        last_tested_at TEXT DEFAULT (datetime('now', '+8 hours')),
        UNIQUE(user_id, topic)
    );
    CREATE INDEX IF NOT EXISTS idx_assessments_user ON lesson_assessments(user_id);
    CREATE INDEX IF NOT EXISTS idx_assessments_lesson ON lesson_assessments(lesson_id);
    CREATE INDEX IF NOT EXISTS idx_mastery_user_topic ON mastery_records(user_id, topic);
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(sql)
    logger.info("quiz DB tables initialized")


# ---- 出题 ----
def generate_quiz_from_lesson(lesson_id: int, user_id: str) -> Optional[Dict[str, Any]]:
    """
    从课程生成一道测验题
    返回 dict 或 None
    """
    # 1. 读取课程内容
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(
            "SELECT id, title, content_md FROM generated_lessons WHERE id = ?",
            (lesson_id,)
        )
        row = c.fetchone()
        if not row:
            return None
        lid, title, content_md = row

    # 2. 用 LLM 出题
    try:
        from lesson_generator import _call_llm

        prompt = f"""你是一位编程教练。根据以下课程内容，设计一道测验题。

课程标题：{title}
课程内容：{content_md[:3000]}

要求：
- 只出 1 道题
- 题型：选择题（给出 A/B/C/D 四个选项）
- 题目要检验学生是否真正理解了这节课的核心概念
- 用户是中文学习者

请按以下 JSON 格式回答，不要有任何其他内容：
{{
  "question": "题目内容（用中文）",
  "question_type": "multiple_choice",
  "options": ["A. 选项内容", "B. 选项内容", "C. 选项内容", "D. 选项内容"],
  "correct_answer": "A"
}}"""

        messages = [
            {"role": "system", "content": "你是一个严谨的出题专家，只回答JSON格式，不要有任何其他文字。"},
            {"role": "user", "content": prompt}
        ]

        raw = _call_llm(messages, temperature=0.5, max_tokens=800)
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if not match:
            logger.warning("LLM 出题失败，无法解析 JSON")
            return None

        data = json.loads(match.group())

        # 3. 存入 lesson_assessments
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO lesson_assessments
                (user_id, lesson_id, question, question_type, correct_answer, options, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id, lid,
                data["question"], data["question_type"],
                data["correct_answer"],
                json.dumps(data.get("options", []), ensure_ascii=False),
                _now()
            ))
            assessment_id = c.lastrowid

        return {
            "id": assessment_id,
            "question": data["question"],
            "options": data.get("options", []),
            "question_type": data["question_type"]
        }

    except Exception as e:
        logger.error("generate_quiz_from_lesson failed: %s", e)
        return None


# ---- 评判 ----
def grade_quiz(assessment_id: int, user_answer: str) -> Dict[str, Any]:
    """
    评判用户答案，返回结果 dict
    """
    # 检测跳过意图
    skip_keywords = ["跳过", "skip", "下一题", "next", "不知道", "not sure"]
    msg_lower = user_answer.lower().strip()
    if any(kw in msg_lower for kw in skip_keywords):
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("""
                UPDATE lesson_assessments
                SET user_answer = 'SKIP', is_correct = 0, answered_at = ?
                WHERE id = ? AND user_answer IS NULL
            """, (_now(), assessment_id))
        return {"is_correct": False, "skipped": True, "correct_answer": ""}

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(
            "SELECT correct_answer, question_type FROM lesson_assessments WHERE id = ?",
            (assessment_id,)
        )
        row = c.fetchone()
        if not row:
            return {"error": "题目不存在"}

        correct, qtype = row
        correct = correct.strip().upper()
        user_ans = user_answer.strip().upper()

        # 选择题：标准化后比对
        if qtype == "multiple_choice":
            m = re.search(r'[A-D]', user_ans)
            user_norm = m.group(0) if m else user_ans
            is_correct = 1 if user_norm == correct else 0
        else:
            is_correct = 0

        # 更新记录
        c.execute("""
            UPDATE lesson_assessments
            SET user_answer = ?, is_correct = ?, answered_at = ?
            WHERE id = ?
        """, (user_answer.strip(), is_correct, _now(), assessment_id))

        return {
            "is_correct": bool(is_correct),
            "correct_answer": correct,
            "user_answer": user_answer
        }


def update_mastery_score(user_id: str, topic: str, score_delta: float, is_correct: bool, lesson_id: int = None):
    """更新知识点掌握度"""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
            INSERT INTO mastery_records (user_id, topic, lesson_id, mastery_score, last_tested_at)
            VALUES (?, ?, ?, 0.5, ?)
            ON CONFLICT(user_id, topic) DO UPDATE SET
                mastery_score = MAX(0.0, MIN(1.0, mastery_score + ?)),
                total_attempts = total_attempts + 1,
                correct_attempts = correct_attempts + CASE WHEN ? THEN 1 ELSE 0 END,
                last_tested_at = ?
        """, (user_id, topic, lesson_id, _now(), score_delta, 1 if is_correct else 0, _now()))


def get_pending_quiz(user_id: str) -> Optional[Dict[str, Any]]:
    """获取用户未作答的题目"""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
            SELECT la.id, la.question, la.options, la.question_type, la.lesson_id
            FROM lesson_assessments la
            WHERE la.user_id = ? AND la.user_answer IS NULL
            ORDER BY la.created_at DESC LIMIT 1
        """, (user_id,))
        row = c.fetchone()
        if not row:
            return None
        opts = json.loads(row[2]) if row[2] else []
        return {
            "id": row[0],
            "question": row[1],
            "options": opts,
            "question_type": row[3],
            "lesson_id": row[4]
        }


def get_mastery_score(user_id: str, topic: str) -> float:
    """获取某个知识点的掌握度"""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT mastery_score FROM mastery_records WHERE user_id = ? AND topic = ?",
                  (user_id, topic))
        row = c.fetchone()
        return row[0] if row else 0.5
