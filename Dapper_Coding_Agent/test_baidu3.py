# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import requests, re

query = '快速排序算法原理'
encoded = requests.utils.quote(query)
url = f'https://www.baidu.com/s?wd={encoded}&rn=5&ie=utf-8'

resp = requests.get(
    url,
    headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    },
    timeout=15
)
resp.encoding = 'utf-8'
html = resp.text

# 尝试不同的正则来匹配结果
patterns = [
    r'<div class="c-container[^"]*"[^>]*>(.*?)</div>\s*</div>',
    r'<h3 class="t".*?</h3>',
    r'<div class="result[^"]*".*?</div>',
    r'data-linkurl="(http[^"]+)"',
]

for i, pat in enumerate(patterns):
    matches = re.findall(pat, html, re.DOTALL)
    print(f'Pattern {i+1}: {len(matches)} matches')
    if matches:
        print(f'  First match (200 chars): {matches[0][:200]}')
        print()

# 找标题和摘要的方法
# 看 html 里有没有 "快速排序"
idx = html.find('快速排序')
if idx > 0:
    print(f'Found "快速排序" at position {idx}')
    print(f'Context: {html[max(0,idx-100):idx+200]}')
else:
    print('"快速排序" NOT found in HTML!')

# 看看是否有反爬
if '验证' in html or 'captcha' in html.lower():
    print('!!! CAPTCHA detected !!!')
