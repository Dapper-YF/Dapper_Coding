# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '/opt/Dapper_Coding_Agent')
import os
os.chdir('/opt/Dapper_Coding_Agent')

from dotenv import load_dotenv
load_dotenv('/opt/Dapper_Coding_Agent/.env')

from tavily import TavilyClient

api_key = os.getenv('TAVILY_API_KEY')
print(f"API Key: {api_key[:20]}...")

client = TavilyClient(api_key=api_key)

try:
    result = client.search("AI news 2026", max_results=3)
    print(f"Results: {len(result.get('results', []))}")
    for r in result.get('results', [])[:2]:
        print(f"  - {r['title'][:50]}")
except Exception as e:
    print(f"Error: {e}")
    print(f"Error type: {type(e)}")
