# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '/opt/Dapper_Coding_Agent')
import os
os.chdir('/opt/Dapper_Coding_Agent')

from dotenv import load_dotenv
load_dotenv('/opt/Dapper_Coding_Agent/.env')

print("Testing dialogue_manager...")
from dialogue_manager import get_dialogue_manager
dm = get_dialogue_manager()
session_id = dm.get_or_create_session('test_user', 'wechat')
dm.add_turn(session_id, 'user', '你好')
dm.add_turn(session_id, 'assistant', '你好！我是 Learning Scout。')
context = dm.build_context('test_user', 'wechat')
print(f"Context: {context}")

print("\nTesting agent_core...")
from agent_core import get_planner
planner = get_planner()
plan = planner.plan("教我学 Python")
print(f"Intent: {plan['intent'].type}")
print(f"Steps: {len(plan['steps'])}")

print("\nTesting tool_executor...")
from tool_executor import get_tool_executor
executor = get_tool_executor()
result = executor.execute('tavily_search', {'query': 'Python 入门教程', 'max_results': 2})
print(f"Search result (first 200 chars): {result[:200]}")

print("\nAll tests passed!")
