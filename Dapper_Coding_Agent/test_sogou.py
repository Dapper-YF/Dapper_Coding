# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import requests, re

# 测试 Sogou 搜索
query = '快速排序算法原理'
encoded = requests.utils.quote(query)
url = f'https://www.sogou.com/web?query={encoded}&ie=utf8'

try:
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
    print(f'Sogou Status: {resp.status_code}')
    print(f'Content length: {len(resp.text)}')
    
    # 查找结果
    if '快速排序' in resp.text:
        idx = resp.text.find('快速排序')
        print(f'Found "快速排序" at {idx}')
        print(f'Context: {resp.text[max(0,idx-50):idx+200]}')
    else:
        print('"快速排序" NOT found')
    
    # 匹配常见结构
    patterns = [
        r'<h3 class="[^"]*"[^>]*>.*?<a[^>]+>(.*?)</a>',
        r'class="vr-title[^"]*"[^>]*>(.*?)</',
        r'<a[^>]+class="[^"]*tit[^"]*"[^>]+>(.*?)</a>',
    ]
    for pat in patterns:
        m = re.findall(pat, resp.text, re.DOTALL)
        if m:
            print(f'Pattern OK: {len(m)} matches, first: {m[0][:100]}')
            break
    else:
        print('No result patterns matched')
        print('HTML前300:', resp.text[:300])
except Exception as e:
    print(f'Error: {e}')
