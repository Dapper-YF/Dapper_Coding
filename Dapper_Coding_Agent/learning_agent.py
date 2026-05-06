# -*- coding: utf-8 -*-
"""
Learning Scout 智能体 - 主循环
整合意图分类、规划、工具执行、反思

Phase 16: LLM 语义意图分类 + Sogou 搜索
P0 修复: 搜索查询清洗 + 中文 Prompt + 无结果重试
"""

import os
import re
import logging
from typing import Optional, List, NamedTuple

logger = logging.getLogger(__name__)


# =============================================================================
# 搜索相关
# =============================================================================

def _sogou_search(query: str, num_results: int = 8, timeout: int = 15) -> str:
    """
    用 Sogou 搜索（中文内容索引好，国内可用）。
    返回合并的 snippets 字符串，失败返回空字符串。
    """
    try:
        import requests
        encoded = requests.utils.quote(query)
        url = f'https://www.sogou.com/web?query={encoded}&ie=utf8'
        resp = requests.get(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept-Language': 'zh-CN,zh;q=0.9',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Referer': 'https://www.sogou.com/',
            },
            timeout=timeout,
            allow_redirects=True
        )
        resp.encoding = 'utf-8'
        if resp.status_code != 200:
            logger.warning(f'Sogou returned status {resp.status_code}')
            return ''

        html = resp.text

        # Sogou 结构: h3 标题 + 后续内容块（包含详细摘要）
        # 提取所有 h3 及其后续内容
        items = re.finditer(r'<h3[^>]*>(.*?)</h3>', html, re.DOTALL)
        snippets = []
        h3_positions = [m.start() for m in re.finditer(r'<h3', html)]

        for i, pos in enumerate(h3_positions):
            chunk_start = pos
            chunk_end = h3_positions[i+1] if i+1 < len(h3_positions) else pos + 1000
            chunk = html[chunk_start:chunk_end]

            # 提取标题
            title_m = re.search(r'<h3[^>]*>(.*?)</h3>', chunk, re.DOTALL)
            if not title_m:
                continue
            title = re.sub(r'<[^>]+>', '', title_m.group(1)).strip()
            if not title or len(title) < 5:
                continue

            # 提取 h3 后的内容作为摘要
            after_h3 = chunk[title_m.end():chunk_end]
            abstract = re.sub(r'<[^>]+>', ' ', after_h3)
            abstract = re.sub(r'\s+', ' ', abstract).strip()
            # 去掉重复标题
            if abstract.startswith(title):
                abstract = abstract[len(title):]
            abstract = abstract.strip()
            # 去掉数字引用和无关字符
            abstract = re.sub(r'^\d+\s*', '', abstract)
            abstract = re.sub(r'<[^>]+>', '', abstract)
            abstract = re.sub(r'\s+', ' ', abstract).strip()

            if len(abstract) > 30:
                snippets.append(f'{title}: {abstract[:300]}')
            else:
                snippets.append(title[:200])

        result = '\n'.join(snippets[:num_results])
        logger.info(f'Sogou: got {len(snippets)} snippets')
        return result
    except Exception as exc:
        logger.warning(f'Sogou search failed: {exc}')
        return ''


def _bing_search(query: str, num_results: int = 5, timeout: int = 10) -> str:
    """
    用 Bing 搜索（fallback 方案）。
    返回合并的 snippets 字符串，失败返回空字符串。
    """
    try:
        import requests
        encoded = requests.utils.quote(query)
        url = f'https://www.bing.com/search?q={encoded}&mkt=zh-cn'
        resp = requests.get(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept-Language': 'zh-CN,zh;q=0.9',
            },
            timeout=timeout,
            allow_redirects=True
        )
        if resp.status_code != 200:
            logger.warning(f'Bing returned status {resp.status_code}')
            return ''

        results = re.findall(r'<li class="b_algo"[^>]*>(.*?)</li>', resp.text, re.DOTALL)
        if not results:
            return ''

        snippets = []
        for r in results[:num_results]:
            title_m = re.search(r'<h2[^>]*>(.*?)</h2>', r, re.DOTALL)
            title = ''
            if title_m:
                title = re.sub(r'<[^>]+>', '', title_m.group(1)).strip()

            p_matches = re.findall(r'<p[^>]*>(.*?)</p>', r, re.DOTALL)
            snippet = ''
            for p in p_matches:
                clean = re.sub(r'<[^>]+>', '', p).strip()
                if len(clean) > 40 and not clean.startswith('http'):
                    snippet = clean
                    break

            if title:
                snippets.append(f'{title}: {snippet}' if snippet else title)

        result = '\n'.join(snippets)
        logger.info(f'Bing: got {len(snippets)} results')
        return result
    except Exception as exc:
        logger.warning(f'Bing search failed: {exc}')
        return ''


def _search(query: str, num_results: int = 8, timeout: int = 15) -> str:
    """
    统一搜索入口：优先 Sogou（中文内容好），fallback Bing。
    """
    result = _sogou_search(query, num_results=num_results, timeout=timeout)
    if not result:
        result = _bing_search(query, num_results=num_results, timeout=timeout)
    return result


def _clean_search_query(user_message: str) -> str:
    """
    从用户消息中提取干净的搜索关键词。

    移除：
    - 图片背景文字（"背景：..." 及之后所有内容）
    - 引号包裹的引用文本
    - 标点符号、特殊字符
    - 多余空格

    提取：中文>=2字的词、英文>=3字的词，合并为搜索 query。
    """
    text = user_message

    # 1. 移除"背景："及其后面的所有内容
    text = re.sub(r'背景[：:].*$', '', text, flags=re.MULTILINE)

    # 2. 移除 Markdown 图片语法 ![alt](url)
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)

    # 3. 移除首尾引号
    text = text.strip('"\'')

    # 4. 移除 Markdown/HTML 标签
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)

    # 5. 提取核心实体词：中文>=2字，英文>=3字
    pattern = r'[\u4e00-\u9fff]{2,}|[a-zA-Z]{3,}'
    terms = re.findall(pattern, text)

    # 6. 去重、保留顺序，取前 8 个词
    seen = set()
    unique_terms = []
    for t in terms:
        t_lower = t.lower()
        if t_lower not in seen:
            seen.add(t_lower)
            unique_terms.append(t)

    core_query = ' '.join(unique_terms[:8])
    return core_query.strip()


def _extract_core_terms(query: str) -> str:
    """
    从已清洗的查询中提取最核心的关键词。
    用于第一次搜索无结果时的重试。
    """
    terms = query.split()
    if len(terms) <= 4:
        return query
    return ' '.join(terms[:5])


# =============================================================================
# 意图分类
# =============================================================================

class IntentClassification(NamedTuple):
    """意图分类结果"""
    intent_type: str
    confidence: float
    reason: str


class LearningAgent:
    """Learning Scout 智能体"""

    INFORMATION_SEEKING_KEYWORDS = [
        '查一下', '帮我查', '查找', '搜索', '找一下',
        '排行', '排名', '多少', '最新', '最近',
        '帮我找', '怎么选', '好不好', '怎么样',
        '是什么', '什么是', '为什么', '如何',
        '介绍一下', '了解', '讲解', '教程',
    ]

    GENERAL_CHAT_KEYWORDS = [
        '你好', '嗨', '嘿', '在吗', '在不在',
        '拜拜', '再见', '晚安', '早上好',
        '谢谢', '好的', '收到', '知道了',
        '哈哈', '呵呵', '有意思', '不错',
    ]

    def __init__(self):
        self._dialogue_manager = None
        self._planner = None
        self._tool_executor = None

    @property
    def dialogue_manager(self):
        if self._dialogue_manager is None:
            from dialogue_manager import get_dialogue_manager
            self._dialogue_manager = get_dialogue_manager()
        return self._dialogue_manager

    @property
    def planner(self):
        if self._planner is None:
            from agent_core import get_planner
            self._planner = get_planner()
        return self._planner

    @property
    def tool_executor(self):
        if self._tool_executor is None:
            from tool_executor import get_tool_executor
            self._tool_executor = get_tool_executor()
        return self._tool_executor

    def classify_intent(self, user_id: str, user_message: str) -> IntentClassification:
        """Phase 16: LLM 语义意图分类器（两级过滤）"""
        level1_result = self._classify_level1(user_id, user_message)
        if level1_result:
            return level1_result
        return self._classify_level2(user_message)

    def _classify_level1(self, user_id: str, user_message: str) -> Optional[IntentClassification]:
        """Level 1: 快速规则（0ms）"""
        msg_lower = user_message.lower()

        # 规则 1: course_related
        try:
            from learning_scout import get_user_conversation, get_latest_generated_lesson
            conv = get_user_conversation(user_id)
            if conv.get("state") == "LEARNING":
                lesson = get_latest_generated_lesson(user_id)
                if lesson:
                    title = lesson.get("title", "")
                    if title:
                        pattern = r'[\u4e00-\u9fff]{2,}|[a-zA-Z]{3,}'
                        title_terms = re.findall(pattern, title.lower())
                        matches = sum(1 for term in title_terms if term in msg_lower)
                        if matches >= 1:
                            return IntentClassification(
                                intent_type="course_related",
                                confidence=0.9,
                                reason="用户在学习状态，消息含课程标题词"
                            )
        except Exception:
            pass

        # 规则 2: information_seeking
        for kw in self.INFORMATION_SEEKING_KEYWORDS:
            if kw in msg_lower:
                return IntentClassification(
                    intent_type="information_seeking",
                    confidence=0.7,
                    reason=f"命中信息查询关键词: {kw}"
                )

        # 规则 3: general_chat
        for kw in self.GENERAL_CHAT_KEYWORDS:
            if kw in msg_lower:
                return IntentClassification(
                    intent_type="general_chat",
                    confidence=0.8,
                    reason=f"命中闲聊关键词: {kw}"
                )

        return None

    def _classify_level2(self, user_message: str) -> IntentClassification:
        """Level 2: LLM 兜底分类"""
        try:
            from lesson_generator import _call_llm
            prompt = f"""用户消息："{user_message}"

判断用户意图，只返回以下选项之一（只返回一个词）：
- course_related：用户想了解/追问当前学习课程的内容
- information_seeking：用户想问一个问题、查资料、了解某个AI/编程/技术信息
- general_chat：用户只是闲聊，寒暄、无明确目的

只返回一个词，不要其他内容。"""
            messages = [{"role": "user", "content": prompt}]
            result = _call_llm(messages, temperature=0.3, max_tokens=10)
            intent_type = result.strip().lower()
            if intent_type not in ("course_related", "information_seeking", "general_chat"):
                intent_type = "information_seeking"
            return IntentClassification(intent_type=intent_type, confidence=0.6, reason="LLM 语义分类")
        except Exception as exc:
            logger.warning("Level 2 LLM 分类失败: %s", exc)
            return IntentClassification(
                intent_type="information_seeking",
                confidence=0.3,
                reason="LLM 不可用，默认信息查询"
            )

    def process_message(self, user_id: str, channel: str, user_message: str) -> str:
        """处理用户消息"""
        logger.info(f"处理消息: user={user_id}, channel={channel}, msg={user_message[:50]}...")

        self.dialogue_manager.add_user_message(user_id, channel, user_message)
        context = self.dialogue_manager.build_context(user_id, channel, limit=10)

        # 优先检测：有没有未答的课后题
        try:
            from quiz_engine import get_pending_quiz, grade_quiz, update_mastery_score
            pending = get_pending_quiz(user_id)
            if pending:
                result = grade_quiz(pending["id"], user_message)
                is_correct = result["is_correct"]
                if is_correct:
                    reply = "回答正确！太棒了！\n\n继续加油，有问题随时问我～"
                    try:
                        from learning_scout import get_latest_generated_lesson
                        lesson = get_latest_generated_lesson(user_id)
                        if lesson:
                            topic = lesson.get("title", "")[:30]
                            update_mastery_score(user_id, topic, 0.2, True, lesson.get("id"))
                    except:
                        pass
                else:
                    reply = (
                        f"不对哦，正确答案是 {result['correct_answer']}\n\n"
                        f"别担心，这正好是学习的好机会！\n"
                        f"可以再看看课程内容，或者直接问我～"
                    )
                    try:
                        from learning_scout import get_latest_generated_lesson
                        lesson = get_latest_generated_lesson(user_id)
                        if lesson:
                            topic = lesson.get("title", "")[:30]
                            update_mastery_score(user_id, topic, -0.3, False, lesson.get("id"))
                    except:
                        pass
                self.dialogue_manager.add_assistant_message(user_id, channel, reply)
                return reply
        except Exception as exc:
            logging.warning("quiz check failed (non-blocking): %s", exc)

        # 语义意图分类
        intent_cls = self.classify_intent(user_id, user_message)
        logger.info(f"意图分类: %s, 置信度: %s, 理由: %s",
                    intent_cls.intent_type, intent_cls.confidence, intent_cls.reason)

        if intent_cls.intent_type == "course_related":
            response = self.teach_with_context(user_id, user_message, context)
            self.dialogue_manager.add_assistant_message(user_id, channel, response)
            return response

        elif intent_cls.intent_type == "information_seeking":
            # information_seeking 走 Sogou 搜索
            response = self._fallback_teach(user_message, context)
            self.dialogue_manager.add_assistant_message(user_id, channel, response)
            return response

        else:  # general_chat
            plan = self.planner.plan(user_message, context)
            intent = plan['intent']
            logger.info(f"意图识别(planner): %s, 置信度: %s", intent.type, intent.confidence)
            results = []
            for step in plan['steps']:
                tool_name = step['tool']
                params = step['params']
                if tool_name == 'llm_chat' and context:
                    params['context'] = context
                result = self.tool_executor.execute(tool_name, params)
                results.append(result)
            response = self._format_response(plan['output_format'], results, intent)
            self.dialogue_manager.add_assistant_message(user_id, channel, response)
            self._reflect(user_id, channel, user_message, response, intent)
            return response

    def teach_with_context(self, user_id: str, user_message: str, context: str = "") -> str:
        """Always use search to answer questions. Lesson content is supplementary context."""
        try:
            from learning_scout import get_latest_generated_lesson
            lesson = get_latest_generated_lesson(user_id)

            # Build enriched context with lesson info as supplementary reference
            enriched_parts = []
            if context:
                enriched_parts.append(f"对话历史：\n{context}")

            if lesson:
                title = lesson.get("title", "")
                level = lesson.get("level", "beginner")
                content_text = lesson.get("content_md", "")[:2000]
                enriched_parts.append(
                    f"用户当前学习课程：{title}\n"
                    f"用户水平：{level}\n"
                    f"课程内容参考：\n{content_text}\n"
                    f"请优先使用搜索结果回答，课程内容仅作为背景参考。"
                )

            enriched_context = "\n\n".join(enriched_parts)
            return self._fallback_teach(user_message, enriched_context)
        except Exception:
            return self._fallback_teach(user_message, context)

    def _fallback_teach(self, user_message: str, context: str = "") -> str:
        """
        Knowledge Q&A with Sogou search + LLM.

        搜索策略：优先 Sogou（中文内容好），fallback Bing。
        """
        # 清洗查询词
        query = _clean_search_query(user_message)
        logger.info(f'清洗后搜索 query: "{query}"')

        # 第一次搜索（用 Sogou）
        search_result = _search(query, num_results=8, timeout=15)
        if not search_result:
            core_terms = _extract_core_terms(query)
            logger.info(f'首次无结果，重试核心词: "{core_terms}"')
            search_result = _search(core_terms, num_results=8, timeout=15)

        # 搜索结果相关性检查
        if search_result:
            preview = search_result[:200]
            query_words = _clean_search_query(user_message).split()[:3]
            matched = sum(1 for w in query_words if w in preview)
            if matched == 0:
                core_terms = _extract_core_terms(query)
                logger.info("Search result irrelevant, retry with: %s", core_terms)
                search_result = _search(core_terms, num_results=8, timeout=15)

        # 用中文 Prompt 调用 LLM（深度回答）
        try:
            from lesson_generator import _call_llm
            if search_result:
                system_prompt = (
                    "你是一个专业、详尽的信息解读专家。请根据搜索结果为用户做出全面、准确、有深度的回答。\n\n"
                    "回答要求：\n"
                    "1. 先给出核心且完整的答案（结论先行）\n"
                    "2. 然后提供详细的解释说明，包含背景、原理、例子等\n"
                    "3. 如果涉及技术内容，请包含代码示例、步骤或图表描述\n"
                    "4. 结构化呈现：使用分点、编号、表格等方式让信息清晰\n"
                    "5. 引用搜索结果中的具体数据和来源\n"
                    "6. 如果搜索结果中没有相关信息，直接说\"目前没有找到相关资料\"，不要编造\n"
                    "7. 不要添加任何标签，如\"AI总结\"、\"内容来源\"等\n"
                    "8. 回答要有足够的深度——不要只给结论，要给出完整的推导和分析过程\n"
                    "9. 【技术/编程类问题】必须包含：代码示例 + 运行结果/输出说明 + 复杂度分析（时间/空间）\n"
                    "10. 【分析/推理类问题】必须包含：推导步骤 + 公式 + 验证方法\n"
                    "11. 【实用/操作类问题】必须包含：具体步骤 + 注意事项 + 常见误区"
                )
                user_prompt_parts = []
                if context:
                    user_prompt_parts.append(f"对话历史：\n{context}")
                user_prompt_parts.append(f"搜索结果：\n{search_result}")
                user_prompt_parts.append(f"用户问题：{user_message}")
                user_prompt = "\n\n".join(user_prompt_parts)
            else:
                return "目前没有找到相关数据，请换个关键词再试试～"

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            return _call_llm(messages, temperature=0.5, max_tokens=1500)
        except Exception as exc:
            logging.error("LLM answer failed: %s", exc)
            return "目前没有找到相关数据，请换个关键词再试试～"

    def _format_response(self, output_format: str, results: List[str], intent) -> str:
        """格式化回复"""
        if not results:
            return "抱歉，我没有找到相关信息。"
        return results[-1]

    def _reflect(self, user_id: str, channel: str, user_msg: str, response: str, intent):
        """反思 - 更新用户记忆"""
        if intent.type in ['learn', 'teach']:
            try:
                from memory import update_user_interests
                update_user_interests(user_id, user_msg)
                logger.info("已更新用户兴趣: user_id=%s, topic=%s", user_id, user_msg[:30])
            except ImportError:
                logger.warning("update_user_interests not found in memory.py")
            except Exception as e:
                logger.warning("更新用户兴趣失败: %s", e)


# 全局实例
_learning_agent: Optional[LearningAgent] = None


def get_learning_agent() -> LearningAgent:
    global _learning_agent
    if _learning_agent is None:
        _learning_agent = LearningAgent()
    return _learning_agent


def process_user_message(user_id: str, channel: str, message: str) -> str:
    """便捷函数：处理用户消息"""
    agent = get_learning_agent()
    return agent.process_message(user_id, channel, message)
