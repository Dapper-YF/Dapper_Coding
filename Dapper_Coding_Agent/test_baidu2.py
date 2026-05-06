# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import requests

query = '快速排序算法原理'
encoded = requests.utils.quote(query)
url = f'https://www.baidu.com/s?wd={encoded}&rn=5&ie=utf-8'

try:
    resp = requests.get(
        url,
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        },
        timeout=15,
        allow_redirects=True
    )
    resp.encoding = 'utf-8'
    print(f'Status: {resp.status_code}')
    print(f'URL: {resp.url}')
    print(f'Content length: {len(resp.text)}')
    print()
    # 检查是否被跳转
    if 'captcha' in resp.text.lower() or '验证' in resp.text:
        print('!!! 可能触发了验证码/验证页面 !!!')
    # 看前500字
    print('HTML前500字:')
    print(resp.text[:500])
except Exception as e:
    print(f'Error: {e}')
