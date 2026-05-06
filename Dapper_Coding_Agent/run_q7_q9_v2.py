# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import os, json, importlib.util

# 加载 .env
env_path = r'E:\Study\Dapper_Coding\.env'
if os.path.exists(env_path):
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, _, value = line.partition('=')
                os.environ[key.strip()] = value.strip().strip('"').strip("'")

spec = importlib.util.spec_from_file_location('la', r'E:\Study\Dapper_Coding\learning_agent.py')
la = importlib.util.module_from_spec(spec)
spec.loader.exec_module(la)

qbank = json.load(open(r'E:\Study\Dapper_Coding\question_bank.json', 'r', encoding='utf-8'))
target_ids = ['Q7', 'Q9']
questions = [q for q in qbank['questions'] if q['id'] in target_ids]

for q in questions:
    print('\n' + '='*60)
    print(f'[{q["id"]}] {q["question"]}')
    print(f'期望关键词: {q.get("expected_tags", [])}')
    print('-'*60)
    try:
        answer = la.process_user_message('local_test', 'local', q['question'])
    except Exception as e:
        answer = f'[ERROR] {e}'
    print(f'回答({len(answer)}字):')
    print(answer[:1500] if len(answer) > 1500 else answer)
    print()
