# -*- coding: utf-8 -*-
# Read the server version and examine the _fallback_teach system_prompt block
with open(r'E:\Study\Dapper_Coding\learning_agent.py', 'rb') as f:
    data = f.read()

# Find second system_prompt = (
first = data.find(b'system_prompt = (')
second = data.find(b'system_prompt = (', first + 1)

# Show all bytes from second occurrence to end of block
block = data[second:17629]  # 17628 is inclusive, so 17629 is after
lines = block.split(b'\n')
print(f'Total lines in block: {len(lines)}')
for i, line in enumerate(lines):
    print(f'  [{i:2}] {repr(line[:120])}')
