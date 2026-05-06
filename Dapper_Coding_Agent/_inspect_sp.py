# -*- coding: utf-8 -*-
with open(r'E:\Study\Dapper_Coding\learning_agent.py', 'rb') as f:
    data = f.read()

# Find second system_prompt = (
idx = data.find(b'system_prompt = (', 16240)
print(f'Second SP at: {idx}')

# Find what comes before - look backwards from idx for a full line
nl_before = data.rfind(b'\n', 0, idx)
line_start = data.rfind(b'\n', 0, nl_before) + 1
prev_line = data[line_start:nl_before]
print(f'Line before: {repr(prev_line)}')
leading = len(prev_line) - len(prev_line.lstrip())
print(f'Leading spaces: {leading}')

# Show the block's first few lines
block_start = nl_before + 1
block = data[block_start:block_start+300]
lines = block.split(b'\n')
for i, line in enumerate(lines[:5]):
    lsp = len(line) - len(line.lstrip())
    print(f'  [{i}] {lsp} spaces: {repr(line[:60])}')

# Show the closing part
up_idx = data.find(b'user_prompt_parts = []')
print(f'user_prompt_parts at: {up_idx}')
# Find closing paren before it - search backwards
for i in range(up_idx - 1, up_idx - 150, -1):
    c = data[i:i+1]
    if c == b')':
        print(f'Closing ) at: {i}')
        print(repr(data[i-20:i+5]))
        break
