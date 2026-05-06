# -*- coding: utf-8 -*-
import subprocess, os

SERVER = "root@8.162.10.45"
KEY = r"C:\Users\Dapper\.ssh\id_rsa_openclaw"
VENV_PY = "/opt/Dapper_Coding_Agent/venv/bin/python3"

script = r"""# -*- coding: utf-8 -*-
import sys, logging
logging.basicConfig(level=logging.INFO)
sys.path.insert(0, '/opt/Dapper_Coding_Agent')
from learning_agent import _bing_search, _clean_search_query, _extract_core_terms

# Test Q1 flow
q1 = "\u5149\u5408\u4F5C\u7528\u662F\u600E\u4E48\u8FDB\u884C\u7684\uFF1F"
print("Q1:", q1)
print("清洗后:", _clean_search_query(q1))
print("核心词:", _extract_core_terms(_clean_search_query(q1)))
print()
r = _bing_search("\u5149\u5408\u4F5C\u7528", num_results=8, timeout=15)
print("搜索结果长度:", len(r) if r else 0)
if r:
    print("前200字:", r[:200])
    print()
    # Check relevance
    qw = _clean_search_query(q1).split()[:3]
    print("查询词:", qw)
    matched = sum(1 for w in qw if w in r[:200])
    print("matched:", matched)
else:
    print("搜索结果: EMPTY")
"""

local_tmp = os.path.join(os.getenv('TEMP', '/tmp'), 'ls_bing_test.py')
with open(local_tmp, 'w', encoding='utf-8') as f:
    f.write(script)

r = subprocess.run(
    ['scp', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=20',
     '-i', KEY, local_tmp, f'{SERVER}:/tmp/ls_bing_test.py'],
    capture_output=True, timeout=30
)
r = subprocess.run(
    ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=60',
     '-i', KEY, SERVER,
     f'PYTHONPATH=/opt/Dapper_Coding_Agent PYTHONIOENCODING=utf-8 {VENV_PY} /tmp/ls_bing_test.py 2>&1'],
    capture_output=True, timeout=120,
    encoding='utf-8', errors='replace'
)
print(r.stdout)
if r.stderr:
    for line in r.stderr.splitlines():
        if any(x in line for x in ['INFO', 'WARNING', 'ERROR']):
            print(line)
