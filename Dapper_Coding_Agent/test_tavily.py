# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '/opt/Dapper_Coding_Agent')
import os
os.chdir('/opt/Dapper_Coding_Agent')

from dotenv import load_dotenv
load_dotenv('/opt/Dapper_Coding_Agent/.env')

print(f"TAVILY_API_KEY: {os.getenv('TAVILY_API_KEY')[:20]}...")

import requests
url = "https://api.tavily.com/search"
params = {
    "q": "Python 教程 2026",
    "api_key": os.getenv('TAVILY_API_KEY'),
    "max_results": 3
}

try:
    resp = requests.get(url, params=params, timeout=30)
    data = resp.json()
    print(f"Status: {resp.status_code}")
    print(f"Results count: {len(data.get('results', []))}")
    if data.get('results'):
        for r in data['results'][:2]:
            print(f"  - {r.get('title', 'N/A')}")
except Exception as e:
    print(f"Error: {e}")
