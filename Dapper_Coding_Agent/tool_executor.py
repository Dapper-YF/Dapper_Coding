# -*- coding: utf-8 -*-
"""
工具执行器 - 统一管理所有工具的注册与执行
Phase 16: Tavily Search 支持
"""

import os
import re
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ToolExecutor:
    """统一工具执行器"""

    def __init__(self):
        self.tavily_api_key = os.environ.get("TAVILY_API_KEY", "")
        self._tavily_client = None

    def _get_tavily_client(self):
        """延迟初始化 Tavily 客户端"""
        if self._tavily_client is None:
            try:
                from tavily import TavilyClient
                self._tavily_client = TavilyClient(api_key=self.tavily_api_key)
            except ImportError:
                logger.warning("Tavily SDK 未安装，搜索功能不可用")
                return None
        return self._tavily_client

    def execute(self, tool_name: str, params: Dict[str, Any]) -> str:
        """执行工具"""
        if tool_name == "tavily_search":
            return self._tavily_search(
                params.get("query", ""),
                params.get("max_results", 5)
            )
        elif tool_name == "llm_chat":
            return self._llm_chat(
                params.get("prompt", ""),
                params.get("context", "")
            )
        elif tool_name == "llm_answer":
            return self._llm_answer(
                params.get("question", ""),
                params.get("context", "")
            )
        else:
            return f"未知工具: {tool_name}"

    def _tavily_search(self, query: str, max_results: int = 5) -> str:
        """Tavily 搜索"""
        if not self.tavily_api_key:
            return "Tavily API Key 未配置"

        try:
            client = self._get_tavily_client()
            result = client.search(
                query,
                max_results=max_results,
                search_depth="advanced",
                include_answer=True
            )

            results = result.get('results', [])
            if not results:
                return "未找到相关结果"

            # 格式化结果
            lines = [f"【{query}相关搜索结果】\n"]
            for i, r in enumerate(results[:5], 1):
                lines.append(f"{i}. {r.get('title', '无标题')}")
                lines.append(f"   {r.get('url', '')}")
                snippet = r.get('description', r.get('content', ''))[:200]
                lines.append(f"   {snippet}...\n")

            # 附加 AI 摘要（不泄露系统标签，让内容自然呈现）
            answer = result.get('answer', '')
            if answer:
                lines.append(f"\n{answer}")

            return '\n'.join(lines)
        except Exception as e:
            logger.error(f"Tavily 搜索失败: {e}")
            return f"搜索失败: {e}"

    def _llm_answer(self, question: str, context: str = "") -> str:
        """LLM 问答"""
        prompt = f"""用户问题：{question}

请根据你的知识回答用户的问题。
回答要：
- 简洁明了
- 适合用户水平
- 如果不确定，可以说明

"""
        if context:
            prompt += f"\n上下文：\n{context}\n"

        return self._call_llm(prompt, max_tokens=500)

    def _llm_chat(self, prompt: str, context: str = "") -> str:
        """通用 LLM 对话"""
        if context:
            prompt = f"{context}\n\n{prompt}"
        return self._call_llm(prompt, max_tokens=800)

    def _call_llm(self, prompt: str, max_tokens: int = 500) -> str:
        """调用 LLM（OpenAI 兼容）"""
        try:
            import openai
            api_key = os.environ.get("OPENAI_API_KEY", "")
            if not api_key:
                return "未配置 OpenAI API Key"

            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.7,
            )
            result = response.model_dump()
            if response and response.choices:
                text = response.choices[0].message.content or ""
                # 移除推理标签，只保留用户可见内容
                import re
                text = re.sub(r'<think>[\s\S]*?
</think>', '', text)
                return text.strip()
            elif 'error' in result:
                return f"LLM 错误: {result['error']}"
            return "LLM 无响应"
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            return f"LLM 调用失败: {e}"


# 全局实例
_tool_executor: Optional[ToolExecutor] = None


def get_tool_executor() -> ToolExecutor:
    global _tool_executor
    if _tool_executor is None:
        _tool_executor = ToolExecutor()
    return _tool_executor
