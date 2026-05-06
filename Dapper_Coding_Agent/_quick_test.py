# -*- coding: utf-8 -*-
import subprocess, os

SERVER = "root@8.162.10.45"
KEY = r"C:\Users\Dapper\.ssh\id_rsa_openclaw"
VENV_PY = "/opt/Dapper_Coding_Agent/venv/bin/python3"
REMOTE_SCRIPT = "/tmp/ls_p0_test.py"

script_content = r"""# -*- coding: utf-8 -*-
import sys, importlib.util
sys.path.insert(0, '/opt/Dapper_Coding_Agent')
spec = importlib.util.spec_from_file_location('la', '/opt/Dapper_Coding_Agent/learning_agent.py')
la = importlib.util.module_from_spec(spec)
spec.loader.exec_module(la)

questions = [
    ("Q1", "\u5149\u5408\u4F5C\u7528\u662F\u600E\u4E48\u8FDB\u884C\u7684\uFF1F"),
    ("Q5", "\u4EC0\u4E48\u662FRESTful API\uFF1F\u5B83\u548C\u666E\u901AAPI\u6709\u4EC0\u4E48\u533A\u522B\uFF1F"),
    ("Q6", "Python\u91CClist\u548Ctuple\u6709\u4EC0\u4E48\u533A\u522B\uFF1F\u4EC0\u4E48\u65F6\u5019\u8BE5\u7528\u54EA\u4E2A\uFF1F"),
    ("Q7", "\u5FEB\u901F\u6392\u5E8F\u662F\u600E\u4E48\u5B9E\u73B0\u7684\uFF1F\u80FD\u5199\u4E2A\u4EE3\u7801\u5417\uFF1F"),
    ("Q9", "Git rebase\u548Cmerge\u6709\u4EC0\u4E48\u533A\u522B\uFF1F\u5404\u81EA\u9002\u7528\u4EC0\u4E48\u573A\u666F\uFF1F"),
]

for qid, question in questions:
    print('='*70)
    print(f'[{qid}] {question}')
    print('-'*70)
    try:
        ans = la.process_user_message('eval', 'ssh', question)
        print(ans[:500] + '...' if len(ans)>500 else ans)
        print(f'字数: {len(ans)}')
    except Exception as e:
        import traceback; traceback.print_exc()
        print(f'ERROR: {e}')
    print()
"""

local_tmp = os.path.join(os.getenv('TEMP', '/tmp'), 'ls_p0_test.py')
with open(local_tmp, 'w', encoding='utf-8') as f:
    f.write(script_content)

# SCP
r = subprocess.run(
    ['scp', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=20',
     '-i', KEY, local_tmp, f'{SERVER}:{REMOTE_SCRIPT}'],
    capture_output=True, timeout=30
)
if r.returncode != 0:
    print(f"SCP failed: {r.stderr}"); exit(1)

print("服务器 P0 测试开始...")
print("="*70)

# Run with venv python + correct path
r = subprocess.run(
    ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=120',
     '-i', KEY, SERVER,
     f'PYTHONPATH=/opt/Dapper_Coding_Agent PYTHONIOENCODING=utf-8 {VENV_PY} {REMOTE_SCRIPT} 2>&1'],
    capture_output=True, timeout=300,
    encoding='utf-8', errors='replace'
)

print(r.stdout)
if r.stderr and ('ERROR' in r.stderr or 'Traceback' in r.stderr or 'Exception' in r.stderr):
    print("STDERR:", r.stderr[:300])
