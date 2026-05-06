# -*- coding: utf-8 -*-
import subprocess, os

SERVER = "root@8.162.10.45"
KEY = r"C:\Users\Dapper\.ssh\id_rsa_openclaw"
VENV_PY = "/opt/Dapper_Coding_Agent/venv/bin/python3"

script = r"""# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '/opt/Dapper_Coding_Agent')
from learning_agent import _extract_core_terms, _bing_search

test_queries = [
    "\u5149\u5408\u4F5C\u7528",  # 光合作用
    "RESTful API",
    "Python list tuple\u533A\u522B",  # Python list tuple区别
    "\u5FEB\u901F\u6392\u5E8F",  # 快速排序
    "Git rebase merge\u533A\u522B",  # Git rebase merge区别
]

for q in test_queries:
    print("="*60)
    print("Query:", q)
    print("Core terms:", _extract_core_terms(q))
    r = _bing_search(q, num_results=8, timeout=15)
    if r:
        print("Results (first 200):", r[:200])
        print("Matched chars:", len(r))
    else:
        print("Results: EMPTY")
    print()
"""

local_tmp = os.path.join(os.getenv('TEMP', '/tmp'), 'ls_search_test.py')
with open(local_tmp, 'w', encoding='utf-8') as f:
    f.write(script)

r = subprocess.run(
    ['scp', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=20',
     '-i', KEY, local_tmp, f'{SERVER}:/tmp/ls_search_test.py'],
    capture_output=True, timeout=30
)
if r.returncode != 0:
    print(f"SCP failed: {r.stderr}"); exit(1)

r = subprocess.run(
    ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=60',
     '-i', KEY, SERVER,
     f'PYTHONPATH=/opt/Dapper_Coding_Agent PYTHONIOENCODING=utf-8 {VENV_PY} /tmp/ls_search_test.py 2>&1'],
    capture_output=True, timeout=120,
    encoding='utf-8', errors='replace'
)
print(r.stdout)
