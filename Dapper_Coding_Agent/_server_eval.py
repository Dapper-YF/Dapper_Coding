# -*- coding: utf-8 -*-
"""
服务器端快速测试 - 通过 SSH 上传脚本、执行、输出结果
"""
import subprocess, json, sys, os, tempfile

SERVER = "root@8.162.10.45"
SSH_KEY = "-o StrictHostKeyChecking=no -o ConnectTimeout=15 -i C:\\Users\\Dapper\\.ssh\\id_rsa_openclaw"
LA_PATH = "/opt/Dapper_Coding_Agent/learning_agent.py"

target_ids = sys.argv[1:] if len(sys.argv) > 1 else ["Q1", "Q5", "Q6", "Q7", "Q9"]

# 加载题库
with open(r'E:\Study\Dapper_Coding\question_bank.json', 'r', encoding='utf-8') as f:
    qbank = json.load(f)
q_map = {q["id"]: q["question"] for q in qbank["questions"]}

print(f"测试目标: {target_ids}")
print(f"Learning Scout 服务器测试")
print("=" * 60)

# 构建远程测试脚本
script_content = [
    "# -*- coding: utf-8 -*-",
    "import sys, importlib.util",
    f"spec = importlib.util.spec_from_file_location('la', '{LA_PATH}')",
    "la = importlib.util.module_from_spec(spec)",
    "spec.loader.exec_module(la)",
    "",
    f"questions = {json.dumps({k: q_map[k] for k in target_ids if k in q_map}, ensure_ascii=False)}",
    "",
    "for qid, question in questions.items():",
    "    print('=' * 60)",
    "    print(f'[{qid}] {question}')",
    "    print('-' * 60)",
    "    try:",
    "        ans = la.process_user_message('eval_bot', 'ssh', question)",
    "        if len(ans) > 500:",
    "            print(ans[:500] + '...')",
    "        else:",
    "            print(ans)",
    "        print(f'字数: {{len(ans)}}')",
    "    except Exception as e:",
    "        import traceback; traceback.print_exc()",
    "        print(f'ERROR: {{e}}')",
    "    print()",
]

remote_script = "/tmp/ls_test.py"
# 上传脚本
script_text = '\n'.join(script_content)
# Write to temp file locally first
tmp_path = os.path.join(os.getenv('TEMP', '/tmp'), 'ls_test.py')
with open(tmp_path, 'w', encoding='utf-8') as f:
    f.write(script_text)

# SCP to server
r = subprocess.run(
    ['scp', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=15',
     '-i', r'C:\Users\Dapper\.ssh\id_rsa_openclaw',
     tmp_path, f'{SERVER}:{remote_script}'],
    capture_output=True, text=True, timeout=30
)
if r.returncode != 0:
    print(f"SCP failed: {r.stderr}")
    sys.exit(1)

print(f"脚本已上传，执行中...")
# SSH 执行
r = subprocess.run(
    ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=30',
     '-i', r'C:\Users\Dapper\.ssh\id_rsa_openclaw', SERVER,
     f'cd /opt/Dapper_Coding_Agent && python3 {remote_script}'],
    capture_output=True, text=True, timeout=120
)

# Decode output (try utf-8, fallback to gbk)
for raw in [r.stdout, r.stderr]:
    if raw:
        for line in raw.splitlines():
            try:
                print(line)
            except:
                print(line.decode('utf-8', errors='replace') if isinstance(line, bytes) else line)
