# -*- coding: utf-8 -*-
with open(r'E:\Study\Dapper_Coding\dapper_coding_agent.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Check for duplicate definitions
import re

# Find all lines that define DIGEST_ENABLED
lines = content.split('\n')
for i, line in enumerate(lines, 1):
    if 'DIGEST_ENABLED = env_bool' in line:
        print(f"Line {i}: {line}")

print("\n--- Checking for WEIXIN_ duplicates ---")
for i, line in enumerate(lines, 1):
    if 'WEIXIN_CORP_ID = os.getenv' in line:
        print(f"Line {i}: {line}")

print("\n--- Checking line counts ---")
print(f"Total lines: {len(lines)}")
