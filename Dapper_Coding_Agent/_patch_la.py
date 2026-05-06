# -*- coding: utf-8 -*-
import subprocess, os

SERVER = "root@8.162.10.45"
KEY = r"C:\Users\Dapper\.ssh\id_rsa_openclaw"
LA_PATH = "/opt/Dapper_Coding_Agent/learning_agent.py"
LOCAL_LA = os.path.join(os.getenv('TEMP', '/tmp'), 'la_patched.py')

print("Downloading...")
r = subprocess.run(
    ['scp', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=20',
     '-i', KEY, f'{SERVER}:{LA_PATH}', LOCAL_LA],
    capture_output=True, timeout=30
)
if r.returncode != 0:
    print(f"SCP failed"); exit(1)

with open(LOCAL_LA, 'rb') as f:
    data = f.read()

# Find _bing_search function start
bing_start = data.find(b'def _bing_search')
print(f"  _bing_search at byte {bing_start}")

# Find '    try:' (try at function level, 4 spaces indent)
try_pos = data.find(b'\n    try:', bing_start)
print(f"  try: at byte {try_pos}")

# The pattern we want: '    """\n    try:'
# The closing docstring line is '    """' (4 spaces, 3 quotes)
# Followed by newline, then '    try:'
# Search backward from try_pos to find the closing docstring
for offset in range(5, 200):
    check_pos = try_pos - offset
    if check_pos < bing_start:
        break
    if data[check_pos:check_pos+7] == b'\n    """':
        # Check: is this preceded by content (not by another """)?
        # The previous 2 chars should NOT be """
        if data[check_pos-1:check_pos+1] != b'"""':
            print(f"  Closing docstring at byte {check_pos+1}")
            print(f"  Context: {repr(data[check_pos:check_pos+30])}")
            break

# Strategy: insert '    import html\n' before '    try:'
# The target sequence is '\n    try:' at try_pos
# We want to replace '\n    try:' with '\n    import html\n    try:'
target = b'\n    try:'
if data[try_pos:try_pos+len(target)] == target:
    data = data[:try_pos] + b'\n    import html' + data[try_pos:]
    print("  PATCH 1: Added '    import html'")
else:
    print(f"  PATCH 1 FAILED: {repr(data[try_pos:try_pos+20])}")
    exit(1)

# html.unescape should already be there from last run
old_result = b"result = '\\n'.join(snippets)"
new_result = b"result = html.unescape('\\n'.join(snippets))"
if old_result in data:
    data = data.replace(old_result, new_result)
    print("  PATCH 2: Added html.unescape")
elif b'html.unescape' in data:
    print("  PATCH 2: already applied")
else:
    print("  PATCH 2: target not found!")

with open(LOCAL_LA, 'wb') as f:
    f.write(data)

# Verify
bing_section = data[data.find(b'def _bing_search'):]
has_import = b'import html' in bing_section
has_unescape = b'html.unescape' in bing_section
print(f"  import html: {has_import}")
print(f"  html.unescape: {has_unescape}")

# Syntax check
r = subprocess.run(['python', '-m', 'py_compile', LOCAL_LA],
    capture_output=True, text=True)
if r.returncode == 0:
    print("  Syntax OK")
else:
    print("  SYNTAX ERROR:", r.stderr[:300])
    exit(1)

print("Uploading...")
r = subprocess.run(
    ['scp', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=20',
     '-i', KEY, LOCAL_LA, f'{SERVER}:{LA_PATH}'],
    capture_output=True, timeout=30
)
if r.returncode != 0:
    print(f"Upload failed: {r.stderr}"); exit(1)

print("Restarting service...")
r = subprocess.run(
    ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=30',
     '-i', KEY, SERVER, 'supervisorctl restart dapper-coding-agent 2>&1'],
    capture_output=True, timeout=30, encoding='utf-8', errors='replace'
)
print(r.stdout)
print("DONE!")
