# -*- coding: utf-8 -*-
"""
意图分类器 - 智能体核心模块
"""

import os
import sys
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

# LLM 调用
import requests

logger = logging.getLogger(__name__)


@dataclass
class Intent:
    """意图"""
    type: str  # 'learn' / 'search' / 'qa' / 'chat' / 'teach'
    params: Dict[str, Any]
    confidence: float


class IntentClassifier:
    """意图分类器"""
    
    # 追问/接话关键词（优先级最高）
    FOLLOWUP_KEYWORDS = [
        '还有呢', '别的方向', '其他方向', '还有', '还有别的',
        '那呢', '然后呢', '接下来', '继续说', '展开讲讲',
        '深入说', '详细点', '具体说说'
    ]

    # 意图关键词
    INTENT_KEYWORDS = {
        'learn': ['教我', '学习', '怎么学', '入门', '教程', '教学', '学会', '掌握', '了解'],
        'search': ['搜索', '查找', '找一下', '查一下', '最新', '最近'],
        'teach': ['生成教学内容', '出题', '练习', '测验', '检验'],
        'qa': ['是什么', '什么是', '为什么', '怎么做', '如何', '多少', '几个'],
        'chat': ['你好', '嗨', '嘿', '在吗', '聊聊天', '随便聊聊']
    }
    
    def classify(self, user_message: str) -> Intent:
        """分类用户意图"""
        message = user_message.lower().strip()

        # 0. 追问/接话检测（优先级最高）
        for kw in self.FOLLOWUP_KEYWORDS:
            if kw in message:
                return Intent(type='followup', params={'keyword': kw}, confidence=0.95)

        # 1. 先用关键词快速匹配
        for intent_type, keywords in self.INTENT_KEYWORDS.items():
            for kw in keywords:
                if kw in message:
                    return Intent(
                        type=intent_type,
                        params={'keyword': kw},
                        confidence=0.8
                    )
        
        # 2. 如果没有匹配，使用 LLM 判断
        return self._classify_with_llm(user_message)
    
    def _classify_with_llm(self, message: str) -> Intent:
        """用 LLM 判断意图"""
        prompt = f"""用户消息："{message}"
判断用户意图，只返回以下选项之一：
- learn：用户想学习某个主题
- search：用户想搜索某个内容
- qa：用户想问一个问题
- teach：用户想生成教学内容/练习
- chat：用户想闲聊

只返回一个词，不要其他内容。"""
        
        try:
            response = self._call_llm(prompt, max_tokens=10)
            intent_type = response.strip().lower()
            
            if intent_type not in ['learn', 'search', 'qa', 'teach', 'chat']:
                intent_type = 'qa'  # 默认问答
            
            return Intent(type=intent_type, params={}, confidence=0.6)
        except Exception as e:
            logger.warning(f"LLM 意图分类失败: {e}，使用默认问答")
            return Intent(type='qa', params={}, confidence=0.5)
    
    def _call_llm(self, prompt: str, max_tokens: int = 100) -> str:
        """调用 LLM"""
        url = os.getenv("LLM_BASE_URL", "https://api.minimax.chat/v1") + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {os.getenv('LLM_API_KEY')}",
            "Content-Type": "application/json"
        }
        data = {
            "model": os.getenv("LLM_MODEL", "MiniMax-M2.7"),
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens
        }
        
        resp = requests.post(url, headers=headers, json=data, timeout=30)
        result = resp.json()
        
        if 'choices' in result:
            return result['choices'][0]['message']['content']
        return "qa"


class Planner:
    """规划器 - 根据意图规划执行步骤"""
    
    def __init__(self):
        self.classifier = IntentClassifier()
    
    def plan(self, user_message: str, context: str = "") -> Dict[str, Any]:
        """规划执行"""
        intent = self.classifier.classify(user_message)
        
        plan_result = {
            'intent': intent,
            'steps': [],
            'output_format': 'text'
        }
        
        if intent.type == 'learn':
            # 学习请求 → 搜索 + 生成教学内容
            plan_result['steps'] = [
                {'tool': 'tavily_search', 'params': {'query': user_message}},
                {'tool': 'generate_teaching', 'params': {'topic': user_message, 'context': context}}
            ]
            plan_result['output_format'] = 'teaching'
        
        elif intent.type == 'teach':
            # 教学请求 → 生成教学内容
            plan_result['steps'] = [
                {'tool': 'generate_teaching', 'params': {'topic': user_message, 'context': context}}
            ]
            plan_result['output_format'] = 'teaching'
        
        elif intent.type == 'search':
            # 搜索请求 → 有上下文时合并到查询
            q = user_message
            if context:
                q = f"{user_message} 背景：{context[-300:]}"
            plan_result['steps'] = [
                {'tool': 'tavily_search', 'params': {'query': q}}
            ]
            plan_result['output_format'] = 'search'
        
        elif intent.type == 'qa':
            # 问答 → RAG + LLM
            plan_result['steps'] = [
                {'tool': 'rag_query', 'params': {'query': user_message}},
                {'tool': 'llm_answer', 'params': {'question': user_message, 'context': context}}
            ]
            plan_result['output_format'] = 'qa'
        
        elif intent.type == 'followup':
            # 追问 → 基于对话历史继续说
            plan_result['steps'] = [
                {'tool': 'llm_answer', 'params': {'question': user_message, 'context': context}}
            ]
            plan_result['output_format'] = 'qa'

        else:  # chat
            # 闲聊 → 直接 LLM
            plan_result['steps'] = [
                {'tool': 'llm_chat', 'params': {'message': user_message, 'context': context}}
            ]
            plan_result['output_format'] = 'chat'

        return plan_result


# 全局实例
_intent_classifier: Optional[IntentClassifier] = None
_planner: Optional[Planner] = None


def get_intent_classifier() -> IntentClassifier:
    global _intent_classifier
    if _intent_classifier is None:
        _intent_classifier = IntentClassifier()
    return _intent_classifier


def get_planner() -> Planner:
    global _planner
    if _planner is None:
        _planner = Planner()
    return _planner
