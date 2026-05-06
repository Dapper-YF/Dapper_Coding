"""
Learning Scout v2 - Lesson Generator 模块
==========================================

给定一个主题，生成一课完整的教学内容（讲解 + 示例 + 练习）。

输入：topic(str) + level + user_background
输出：Lesson dataclass（结构化课程内容）
"""

import json
import logging
import os
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Literal, Optional

# 加载环境变量
sys_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, sys_path)
try:
    from learning_scout import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, load_local_env
    load_local_env()
except ImportError:
    LLM_API_KEY = os.getenv("LLM_API_KEY", "")
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.minimax.chat/v1")
    LLM_MODEL = os.getenv("LLM_MODEL", "minimax-m2.7")

# ============================================================
# 数据结构
# ============================================================

@dataclass
class CodeExample:
    """代码示例"""
    description: str          # 示例说明
    code: str                # 代码内容
    language: str = "python" # 编程语言
    expected_output: str = "" # 预期输出（可选）
    filename: str = ""       # 文件名（可选）


@dataclass
class Exercise:
    """练习题"""
    question: str            # 题目描述
    hints: List[str] = field(default_factory=list)  # 提示
    answer: str = ""         # 参考答案
    explanation: str = ""     # 答案解析


@dataclass
class LessonSection:
    """课程章节"""
    heading: str             # 章节标题
    content: str             # 讲解内容（Markdown）
    code_examples: List[CodeExample] = field(default_factory=list)


@dataclass
class Lesson:
    """完整课程"""
    title: str
    topic: str
    level: str
    summary: str             # 课程总结
    sections: List[LessonSection] = field(default_factory=list)
    code_examples: List[CodeExample] = field(default_factory=list)
    exercises: List[Exercise] = field(default_factory=list)
    estimated_minutes: int = 30


# ============================================================
# Prompt 模板
# ============================================================

LESSON_SYSTEM_PROMPT = """你是一位专业的编程教育助手，擅长用简洁清晰的语言讲解技术概念。

你的职责是根据用户给定的主题，生成一节完整的课程内容。

## 输出要求

请严格按照以下 JSON 格式输出，不要包含任何非 JSON 内容：

{
  "title": "课程标题",
  "summary": "3-5句话的课程总结",
  "estimated_minutes": 数字（课程时长分钟数）,
  "sections": [
    {
      "heading": "章节标题",
      "content": "Markdown 格式的讲解内容",
      "code_examples": [
        {
          "description": "示例说明",
          "code": "代码内容",
          "language": "python",
          "expected_output": "预期输出（可选）",
          "filename": "文件名.py（可选）"
        }
      ]
    }
  ],
  "code_examples": [
    {
      "description": "综合示例说明",
      "code": "完整可运行代码",
      "language": "python",
      "expected_output": "运行结果"
    }
  ],
  "exercises": [
    {
      "question": "题目描述",
      "hints": ["提示1", "提示2"],
      "answer": "参考答案代码",
      "explanation": "详细解答思路"
    }
  ]
}

## 质量标准

- sections 至少包含 2 个章节
- code_examples 中的代码必须语法正确、可运行
- exercises 必须有 2-4 道题，且答案解析详细
- 内容要贴合用户背景，用用户能理解的语言讲解
- 技术概念要给出具体代码示例
- 难度级别：beginner（入门）、intermediate（中级）、advanced（高级）"""


def build_lesson_user_prompt(topic: str, level: str, user_background: str = "", adaptive_mode: str = "normal") -> str:
    """构建用户 Prompt"""
    background_section = f"\n\n## 用户背景\n{user_background}" if user_background else ""
    return f"""## 任务
生成一节关于「{topic}」的课程。

## 难度级别
{level}

{background_section}

## 要求
请生成一节{"精简版" if adaptive_mode == "fast" else "完整版"}课程，包含：
1. {"1-2" if adaptive_mode == "fast" else "2-4"} 个章节（{"精讲核心重点" if adaptive_mode == "fast" else "讲解核心概念"}）
2. {"1-2" if adaptive_mode == "fast" else "3-5"} 个代码示例（必须可运行）
3. {"1-2" if adaptive_mode == "fast" else "2-4"} 道练习题（带答案和解析）
{"【压缩模式】课程要精炼简洁，直击要点。" if adaptive_mode == "fast" else ""}
{"【强化模式】多举例，多对比，帮助用户彻底理解。" if adaptive_mode == "reinforce" else ""}

严格按照上述 JSON 格式输出。"""


# ============================================================
# LLM 调用
# ============================================================

def _call_llm(messages: List[Dict[str, str]], model: str = None, temperature: float = 0.7, max_tokens: int = 0) -> str:
    """调用 LLM API"""
    model = model or LLM_MODEL
    url = f"{LLM_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    if max_tokens > 0:
        payload["max_tokens"] = max_tokens
    try:
        import requests as _requests
        resp = _requests.post(url, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception as exc:
        logging.error("LLM 调用失败: %s", exc)
        raise


# ============================================================
# 解析与构建
# ============================================================

def _extract_json(text: str) -> Optional[str]:
    """从 LLM 输出中提取 JSON 块"""
    # 优先找 markdown 代码块
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        return match.group(1)
    # 其次找纯 JSON 对象
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        return match.group(0)
    return None


def _parse_lesson(data: Dict[str, Any]) -> Lesson:
    """将 JSON dict 解析为 Lesson 对象"""
    sections = []
    for s in data.get("sections", []):
        code_examples = []
        for ce in s.get("code_examples", []):
            code_examples.append(CodeExample(
                description=ce.get("description", ""),
                code=ce.get("code", ""),
                language=ce.get("language", "python"),
                expected_output=ce.get("expected_output", ""),
                filename=ce.get("filename", ""),
            ))
        sections.append(LessonSection(
            heading=s.get("heading", ""),
            content=s.get("content", ""),
            code_examples=code_examples,
        ))

    code_examples = []
    for ce in data.get("code_examples", []):
        code_examples.append(CodeExample(
            description=ce.get("description", ""),
            code=ce.get("code", ""),
            language=ce.get("language", "python"),
            expected_output=ce.get("expected_output", ""),
            filename=ce.get("filename", ""),
        ))

    exercises = []
    for ex in data.get("exercises", []):
        exercises.append(Exercise(
            question=ex.get("question", ""),
            hints=ex.get("hints", []),
            answer=ex.get("answer", ""),
            explanation=ex.get("explanation", ""),
        ))

    return Lesson(
        title=data.get("title", ""),
        topic=data.get("topic", ""),
        level=data.get("level", ""),
        summary=data.get("summary", ""),
        sections=sections,
        code_examples=code_examples,
        exercises=exercises,
        estimated_minutes=data.get("estimated_minutes", 30),
    )


def _build_fallback_lesson(topic: str, level: str) -> Lesson:
    """生成失败时的兜底课程"""
    return Lesson(
        title=f"{topic} 课程",
        topic=topic,
        level=level,
        summary=f"本课程带你入门 {topic}，包含核心概念讲解和实践练习。",
        sections=[
            LessonSection(
                heading="什么是" + topic,
                content=f"这一节我们介绍 {topic} 的基本概念。\n\n{topic} 是现代编程中非常重要的概念，建议认真学习。",
                code_examples=[],
            ),
            LessonSection(
                heading="快速上手",
                content=f"让我们通过一个简单示例来认识 {topic}：\n\n```python\n# {topic} 示例\nprint('Hello, {topic}!')\n```",
                code_examples=[
                    CodeExample(
                        description=f"{topic} 基础示例",
                        code=f"# 基础示例\nprint('Welcome to {topic}!')",
                        language="python",
                    )
                ],
            ),
        ],
        code_examples=[
            CodeExample(
                description="综合示例",
                code=f"# {topic} 综合示例\nresult = '{topic}'\nprint(f'Learning: {{result}}')",
                language="python",
            )
        ],
        exercises=[
            Exercise(
                question=f"尝试写一段代码，使用 {topic} 的基本特性",
                hints=["从简单开始", "参考上面的示例"],
                answer=f"print('{topic}')",
                explanation="本题没有标准答案，只要正确使用 topic 即可。",
            )
        ],
        estimated_minutes=20,
    )


# ============================================================
# 主函数
# ============================================================

def generate_lesson(
    topic: str,
    level: str = "beginner",
    user_background: str = "",
    model: str = None,
    adaptive_mode: str = "normal",
) -> Lesson:
    """
    生成一节课程

    参数：
        topic: 课程主题
        level: 难度级别（beginner / intermediate / advanced）
        user_background: 用户背景描述
        model: 可选的模型覆盖

    返回：
        Lesson 对象
    """
    logging.info("生成课程: topic=%s, level=%s, mode=%s", topic, level, adaptive_mode)

    messages = [
        {"role": "system", "content": LESSON_SYSTEM_PROMPT},
        {"role": "user", "content": build_lesson_user_prompt(topic, level, user_background, adaptive_mode)},
    ]

    try:
        text = _call_llm(messages, model=model)
        raw = _extract_json(text)
        if not raw:
            logging.warning("无法从 LLM 输出中提取 JSON，使用兜底课程")
            return _build_fallback_lesson(topic, level)

        if not raw:
            logging.warning("无法从 LLM 输出中提取 JSON，使用兜底课程")
            return _build_fallback_lesson(topic, level)

        data = json.loads(raw)
        lesson = _parse_lesson(data)
        # 质量门禁检查
        if len(lesson.sections) < 2:
            logging.warning("sections 少于 2 个，使用兜底课程")
            return _build_fallback_lesson(topic, level)
        if len(lesson.exercises) < 2:
            logging.warning("exercises 少于 2 道，使用兜底课程")
            return _build_fallback_lesson(topic, level)

        logging.info("课程生成成功: %s (%d 分钟)", lesson.title, lesson.estimated_minutes)
        return lesson

    except json.JSONDecodeError as exc:
        logging.error("JSON 解析失败: %s，尝试修复...", exc)
        try:
            if not raw:
                raise ValueError("raw is None")
            # 尝试修复常见 JSON 问题
            cleaned = raw.replace("```", "").strip()
            # 移除尾随逗号
            cleaned = re.sub(r",(\s*[}\]])", r"\1", cleaned)
            data = json.loads(cleaned)
            lesson = _parse_lesson(data)
            # 质量门禁检查
            if len(lesson.sections) < 2 or len(lesson.exercises) < 2:
                raise ValueError("Quality gate failed")
            logging.info("JSON 修复成功: %s", lesson.title)
            return lesson
        except Exception:
            logging.warning("JSON 修复也失败了，使用兜底课程")
            return _build_fallback_lesson(topic, level)

    except Exception as exc:
        logging.error("课程生成异常: %s，使用兜底课程", exc)
        return _build_fallback_lesson(topic, level)


# ============================================================
# 格式化输出
# ============================================================

def format_lesson_markdown(lesson: Lesson) -> str:
    """
    将 Lesson 对象格式化为 Markdown 字符串，
    便于在企业微信等平台展示。
    """
    lines = [
        f"# {lesson.title}",
        "",
        f"> 📚 {lesson.level} · ⏱ {lesson.estimated_minutes} 分钟",
        "",
        f"**摘要：** {lesson.summary}",
        "",
        "---",
        "",
    ]

    # 章节
    for i, section in enumerate(lesson.sections, 1):
        lines.append(f"## {i}. {section.heading}")
        lines.append("")
        lines.append(section.content)
        lines.append("")

        if section.code_examples:
            for ce in section.code_examples:
                if ce.filename:
                    lines.append(f"**📁 {ce.filename}**")
                lines.append(f"**{ce.description}**")
                lines.append(f"```{ce.language}\n{ce.code}\n```")
                if ce.expected_output:
                    lines.append(f"> 输出：{ce.expected_output}")
                lines.append("")

    # 综合示例
    if lesson.code_examples:
        lines.append("---")
        lines.append("")
        lines.append("## 📝 综合示例")
        lines.append("")
        for ce in lesson.code_examples:
            if ce.filename:
                lines.append(f"**📁 {ce.filename}**")
            lines.append(f"**{ce.description}**")
            lines.append(f"```{ce.language}\n{ce.code}\n```")
            if ce.expected_output:
                lines.append(f"> 输出：{ce.expected_output}")
            lines.append("")

    # 练习
    if lesson.exercises:
        lines.append("---")
        lines.append("")
        lines.append("## 🎯 练习题")
        lines.append("")
        for i, ex in enumerate(lesson.exercises, 1):
            lines.append(f"**{i}. {ex.question}**")
            if ex.hints:
                lines.append(f"> 💡 提示：{' | '.join(ex.hints)}")
            lines.append("")

    # 答案解析
    if lesson.exercises and any(ex.answer for ex in lesson.exercises):
        lines.append("---")
        lines.append("")
        lines.append("## ✅ 答案与解析")
        lines.append("")
        for i, ex in enumerate(lesson.exercises, 1):
            if ex.answer:
                lines.append(f"**{i}. {ex.question}**")
                lines.append(f"```python\n{ex.answer}\n```")
            if ex.explanation:
                lines.append(f"> {ex.explanation}")
            lines.append("")

    return "\n".join(lines)


# ============================================================
# 调试入口
# ============================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    import sys
    if len(sys.argv) > 1:
        topic = sys.argv[1]
        level = sys.argv[2] if len(sys.argv) > 2 else "beginner"
        bg = sys.argv[3] if len(sys.argv) > 3 else ""
    else:
        topic = "Python 变量和数据类型"
        level = "beginner"
        bg = "零基础编程学习者"

    lesson = generate_lesson(topic, level, bg)
    md = format_lesson_markdown(lesson)
    print(md)
