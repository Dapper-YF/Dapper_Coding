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

# 找所有包含"快速排序"的 h3 及其上下文
h3_positions = [m.start() for m in re.finditer(r'<h3', html)]
print(f'Found {len(h3_positions)} h3 tags')

for pos in h3_positions[:5]:
    chunk = html[pos:pos+500]
    # 清理标签
    text = re.sub(r'<[^>]+>', ' ', chunk)
    text = re.sub(r'\s+', ' ', text).strip()
    print(f'--- h3 chunk ---')
    print(text[:300])
    print()
