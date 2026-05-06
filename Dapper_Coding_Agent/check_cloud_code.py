# -*- coding: utf-8 -*-
# 检查 run_tech_digest 是否有详细的日志输出
with open(r'E:\Study\Dapper_Coding\tech_digest.py', 'r', encoding='utf-8') as f:
    content = f.read()

print("run_tech_digest found:", 'def run_tech_digest' in content)

# Find key log statements
import re
for pattern in ['logging.info', 'logging.error', 'logging.warning']:
    matches = list(re.finditer(pattern, content))
    print(f"{pattern}: {len(matches)} occurrences")
    if matches:
        # Show first one
        idx = matches[0].start()
        print(f"  Example: {content[idx-30:idx+80]}")
