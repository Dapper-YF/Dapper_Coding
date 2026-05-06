# -*- coding: utf-8 -*-
import re, json

with open(r'E:\Study\Dapper_Coding\_run_eval.py', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

# Try to find question arrays
# Look for patterns like 'Q1:': ['question text', ...]
pattern = re.compile(r'["\u201c]([^"\u201d]+)["\u201d]\s*[,\]:]', re.UNICODE)
matches = pattern.findall(content)
print(f'Found {len(matches)} potential question strings')
for i, m in enumerate(matches[:40]):
    if len(m) > 10:
        print(f'  [{i}] {m[:80]}')
