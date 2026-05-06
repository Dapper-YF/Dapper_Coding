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

# 搜索标题 + 摘要的组合
# 常见模式: h3 + 后续的 p 标签内容
# 找到所有 h3 tag 及其后的内容块
items = re.finditer(r'<h3[^>]*>(.*?)</h3>', html, re.DOTALL)

snippets = []
for i, m in enumerate(items):
    title = re.sub(r'<[^>]+>', '', m.group(1)).strip()
    if not title or len(title) < 5:
        continue
    # 找 h3 后面跟随的摘要内容
    start = m.end()
    end = start + 500
    chunk = html[start:end]
    # 找下一个 h3 或相近的块
    next_h3 = re.search(r'<h3', chunk)
    if next_h3:
        chunk = chunk[:next_h3.start()]
    # 提取纯文本
    abstract = re.sub(r'<[^>]+>', ' ', chunk)
    abstract = re.sub(r'\s+', ' ', abstract).strip()
    # 去掉标题重复部分
    if abstract.startswith(title):
        abstract = abstract[len(title):]
    abstract = abstract.strip()
    if len(abstract) > 30:
        snippets.append(f'{title}: {abstract[:200]}')
    else:
        snippets.append(title)

print(f'Got {len(snippets)} snippets:')
for s in snippets[:8]:
    print(f'  - {s[:200]}')
    print()
