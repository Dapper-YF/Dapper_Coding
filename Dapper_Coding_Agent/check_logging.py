# -*- coding: utf-8 -*-
with open(r'E:\Study\Dapper_Coding\dapper_coding_agent.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the main block
idx = content.find('if __name__ == "__main__"')
if idx > 0:
    print("Found main block at:", idx)
    print(content[idx:idx+3000])
else:
    print("Main block not found")
