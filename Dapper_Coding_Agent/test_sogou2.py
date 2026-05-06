# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import requests, re

query = '快速排序算法原理'
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
    timeout=15
)
resp.encoding = 'utf-8'
html = resp.text

# 提取搜索结果 - Sogou 结构
# 结果通常在 <ul class="results"> 下的 <li class="vr-result">
results = re.findall(r'<li class="[^"]*result[^"]*"[^>]*>(.*?)</li>', html, re.DOTALL)
print(f'Found {len(results)} results (li.result)')

if not results:
    results = re.findall(r'<div class="vr-title[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL)
    print(f'Found {len(results)} vr-title divs')

if not results:
    # 试一下 h3 标题
    results = re.findall(r'<h3[^>]*>(.*?)</h3>', html, re.DOTALL)
    print(f'Found {len(results)} h3 tags')

print()
snippets = []
for i, r in enumerate(results[:8]):
    # 清理 HTML 标签，保留纯文本
    text = re.sub(r'<[^>]+>', '', r).strip()
    text = re.sub(r'\s+', ' ', text)
    if len(text) > 20:
        snippets.append(text[:200])
        print(f'[{i}] {text[:200]}')
        print()

print()
print('Combined snippets:')
print('\n'.join(snippets[:5]))
