# -*- coding: utf-8 -*-
import subprocess, os

SERVER = "root@8.162.10.45"
KEY = r"C:\Users\Dapper\.ssh\id_rsa_openclaw"
VENV_PY = "/opt/Dapper_Coding_Agent/venv/bin/python3"

script = r"""import sys
sys.path.insert(0, '/opt/Dapper_Coding_Agent')
try:
    import html
    print('html module OK:', html.__file__)
except ImportError as e:
    print('html module NOT available:', e)
"""

local_tmp = os.path.join(os.getenv('TEMP', '/tmp'), 'ls_html_test.py')
with open(local_tmp, 'w', encoding='utf-8') as f:
    f.write(script)

r = subprocess.run(
    ['scp', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=20',
     '-i', KEY, local_tmp, f'{SERVER}:/tmp/ls_html_test.py'],
    capture_output=True, timeout=30
)
r = subprocess.run(
    ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=30',
     '-i', KEY, SERVER, f'{VENV_PY} /tmp/ls_html_test.py 2>&1'],
    capture_output=True, timeout=60,
    encoding='utf-8', errors='replace'
)
print(r.stdout)
