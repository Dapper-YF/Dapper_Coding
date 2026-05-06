# -*- coding: utf-8 -*-
"""
Learning Scout 智能体 - 主循环
整合意图分类、规划、工具执行、反思
"""

import os
import sys
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)


class LearningAgent:
    """Learning Scout 智能体"""
    
    def __init__(self):
        # 延迟导入，避免循环依赖
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
    
    def process_message(self, user_id: str, channel: str, user_message: str) -> str:
        """处理用户消息"""
        logger.info(f"处理消息: user={user_id}, channel={channel}, msg={user_message[:50]}...")
        
        # 1. 添加用户消息到对话历史
        self.dialogue_manager.add_user_message(user_id, channel, user_message)
        
        # 2. 获取对话上下文
        context = self.dialogue_manager.build_context(user_id, channel, limit=10)
        
        # 2.5 Check if this is a learning context query (dialogue teaching)
        if self._is_learning_query(user_id, user_message):
            response = self.teach_with_context(user_id, user_message)
            self.dialogue_manager.add_assistant_message(user_id, channel, response)
            return response

        # 3. 意图分类 & 规划
        plan = self.planner.plan(user_message, context)
        intent = plan['intent']
        
        logger.info(f"意图识别: {intent.type}, 置信度: {intent.confidence}, 步骤数: {len(plan['steps'])}")
        
        # 4. 执行计划
        results = []
        for step in plan['steps']:
            tool_name = step['tool']
            params = step['params']
            
            if tool_name == 'llm_answer' and context:
                params['context'] = context
            elif tool_name == 'llm_chat' and context:
                params['context'] = context
            elif tool_name == 'generate_teaching' and context:
                params['context'] = context
            
            result = self.tool_executor.execute(tool_name, params)
            results.append(result)
        
        # 5. 组装回复
        response = self._format_response(plan['output_format'], results, intent)
        
        # 6. 添加助手回复到对话历史
        self.dialogue_manager.add_assistant_message(user_id, channel, response)
        
        # 7. 反思 - 更新用户画像
        self._reflect(user_id, channel, user_message, response, intent)
        
        return response
    
    def _is_learning_query(self, user_id: str, user_message: str) -> bool:
        try:
            from learning_scout import get_user_conversation
            conv = get_user_conversation(user_id)
            if conv.get("state") != "LEARNING":
                return False
            keywords = [
                "what is", "how", "why", "explain", "tell me", "not understand", "confused", "explain again",
                "是什么", "怎么", "如何", "为什么", "不懂", "不会", "不清楚", "解释", "例子", "概念", "什么意思",
            ]
            return any(kw in user_message.lower() for kw in keywords)
        except Exception:
            return False

    def teach_with_context(self, user_id: str, user_message: str) -> str:
        try:
            from learning_scout import get_generated_lesson, get_user_current_topic
            topic, level, direction = get_user_current_topic(user_id)
            if not topic or not direction:
                return self._fallback_teach(user_message)
            from learning_scout import get_user_conversation
            conv = get_user_conversation(user_id)
            current_day = conv.get("current_day", 1)
            lesson = get_generated_lesson(user_id, direction, current_day)
            if not lesson:
                return self._fallback_teach(user_message)
            from lesson_generator import _call_llm
            system_prompt = f"You are a patient programming tutor. Difficulty: {level}. Answer concisely."
            content_text = lesson.get("content_md", "")[:2000]
            user_prompt = f"Course content:\n{content_text}\n\nUser question: {user_message}\n\nAnswer based on course context."
            messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
            reply = _call_llm(messages, temperature=0.5, max_tokens=1000)
            return reply
        except Exception as exc:
            return self._fallback_teach(user_message)

    def _fallback_teach(self, user_message: str) -> str:
        try:
            from lesson_generator import _call_llm
            messages = [{"role": "system", "content": "You are a programming tutor. Answer concisely."}, {"role": "user", "content": user_message}]
            return _call_llm(messages, temperature=0.5, max_tokens=800)
        except Exception:
            return "Sorry, I cannot answer right now."

    def _format_response(self, output_format: str, results: List[str], intent) -> str:
        """格式化回复"""
        if not results:
            return "抱歉，我没有找到相关信息。"
        
        if output_format == 'teaching':
            return results[-1]
        elif output_format == 'search':
            return results[-1]
        elif output_format == 'qa':
            return results[-1]
        elif output_format == 'chat':
            return results[-1]
        
        return results[-1]
    
    def _reflect(self, user_id: str, channel: str, user_msg: str, response: str, intent):
        """反思 - 更新用户记忆"""
        if intent.type in ['learn', 'teach']:
            # 用户想学习，更新兴趣标签
            try:
                from memory import update_user_interests
                update_user_interests(user_id, user_msg)
                logger.info(f"已更新用户兴趣: user_id={user_id}, topic={user_msg[:30]}")
            except ImportError:
                logger.warning("update_user_interests not found in memory.py")
            except Exception as e:
                logger.warning(f"更新用户兴趣失败: {e}")


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
