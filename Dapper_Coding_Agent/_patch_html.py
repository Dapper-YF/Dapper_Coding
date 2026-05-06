# -*- coding: utf-8 -*-
import subprocess, os

SERVER = "root@8.162.10.45"
KEY = r"C:\Users\Dapper\.ssh\id_rsa_openclaw"
VENV_PY = "/opt/Dapper_Coding_Agent/venv/bin/python3"
LA_PATH = "/opt/Dapper_Coding_Agent/learning_agent.py"

# Build a server-side patch script
# Strategy: read learning_agent.py, patch in-memory, write back
patch_py = r"""
import re

fpath = '/opt/Dapper_Coding_Agent/learning_agent.py'
with open(fpath, 'r', encoding='utf-8') as f:
    content = f.read()

orig = content

# Patch 1: add 'import html' inside _bing_search try block
# Find the try: line in _bing_search and add import html after it
bing_func = content.split('def _bing_search')[1].split('def ')[0]
if 'import html' not in bing_func:
    lines = bing_func.split('\n')
    new_lines = []
    for line in lines:
        new_lines.append(line)
        if line.strip() == 'try:':
            new_lines.append('    import html')
    new_bing = '\n'.join(new_lines)
    content = content.split('def _bing_search')[0] + 'def _bing_search' + new_bing + 'def ' + content.split('def _bing_search')[1].split('def ', 1)[1]
    print('PATCH 1: Added import html')
else:
    print('PATCH 1: import html already present')

# Patch 2: wrap result with html.unescape
# The line is: result = '\n'.join(snippets)
old_line = "result = '\\n'.join(snippets)"
if old_line in content:
    content = content.replace(old_line, "result = html.unescape('\\n'.join(snippets))")
    print('PATCH 2: Added html.unescape')
else:
    # Try to find what's there
    idx = content.find("result = ")
    if idx >= 0:
        print('Found result line:', repr(content[idx:idx+50]))
    print('PATCH 2: FAILED to find target')

with open(fpath, 'w', encoding='utf-8') as f:
    f.write(content)

print('Written to', fpath)

# Verify
with open(fpath, 'r', encoding='utf-8') as f:
    v = f.read()
bb = v.split('def _bing_search')[1].split('def ')[0]
check1 = 'import html' in bb
check2 = 'html.unescape' in bb
print('VERIFIED import html:', check1)
print('VERIFIED html.unescape:', check2)
if not (check1 and check2):
    print('ERROR: patches not applied correctly')
    exit(1)
"""

local_tmp = os.path.join(os.getenv('TEMP', '/tmp'), 'ls_patch.py')
with open(local_tmp, 'w', encoding='utf-8') as f:
    f.write(patch_py)

r = subprocess.run(
    ['scp', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=20',
     '-i', KEY, local_tmp, f'{SERVER}:/tmp/ls_patch.py'],
    capture_output=True, timeout=30
)
if r.returncode != 0:
    print(f"SCP failed"); exit(1)

print("Applying patch...")
r = subprocess.run(
    ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=60',
     '-i', KEY, SERVER, f'{VENV_PY} /tmp/ls_patch.py 2>&1'],
    capture_output=True, timeout=60,
    encoding='utf-8', errors='replace'
)
print(r.stdout)
if r.stderr and r.stderr.strip():
    print("STDERR:", r.stderr[:200])

print("\nRestarting service...")
r = subprocess.run(
    ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=30',
     '-i', KEY, SERVER, 'supervisorctl restart dapper-coding-agent 2>&1'],
    capture_output=True, timeout=30,
    encoding='utf-8', errors='replace'
)
print(r.stdout)
print("Done!")
