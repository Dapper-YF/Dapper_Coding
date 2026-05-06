# -*- coding: utf-8 -*-
import requests

TAVILY_API_KEY = "YOUR_TAVILY_API_KEY"

# Try different search queries
queries = [
    "WeChat Work group robot webhook API",
    "企业微信 群机器人 开发文档",
    "WeChat Work bot development tutorial"
]

for query in queries:
    print(f"\n=== Searching: {query} ===")
    url = "https://api.tavily.com/search"
    params = {
        "q": query,
        "api_key": TAVILY_API_KEY,
        "max_results": 5
    }
    
    try:
        resp = requests.get(url, params=params, timeout=30)
        data = resp.json()
        results = data.get("results", [])
        print(f"Found {len(results)} results")
        for i, r in enumerate(results[:3], 1):
            print(f"  {i}. {r.get('title', 'N/A')}")
            print(f"     {r.get('url', 'N/A')}")
    except Exception as e:
        print(f"  Error: {e}")
