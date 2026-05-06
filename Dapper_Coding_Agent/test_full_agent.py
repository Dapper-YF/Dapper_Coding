# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '/opt/Dapper_Coding_Agent')
import os
os.chdir('/opt/Dapper_Coding_Agent')

from dotenv import load_dotenv
load_dotenv('/opt/Dapper_Coding_Agent/.env')

print("1. Testing learning_agent...")
from learning_agent import get_learning_agent
agent = get_learning_agent()

print("\n2. Processing message: '教我学 Python'")
response = agent.process_message('test_user', 'wechat', '教我学 Python')
print(f"Response (first 500 chars):\n{response[:500]}")
print("\n=== TEST PASSED ===")
