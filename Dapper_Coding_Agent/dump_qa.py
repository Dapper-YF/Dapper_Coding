# -*- coding: utf-8 -*-
import json, sys

# Set stdout encoding to UTF-8
sys.stdout.reconfigure(encoding='utf-8')

f1 = open(r'E:\Study\Dapper_Coding\eval_baseline_answers.json', 'r', encoding='utf-8')
f2 = open(r'E:\Study\Dapper_Coding\eval_ls_answers.json', 'r', encoding='utf-8')
bl = json.load(f1)
ls = json.load(f2)
f1.close()
f2.close()

for i in range(len(bl)):
    q = bl[i]['question']
    bl_ans = bl[i]['answer']
    ls_ans = ls[i]['answer']
    dim = bl[i].get('dimension', 'N/A')
    diff = bl[i].get('difficulty', 'N/A')
    print(f"\n{'='*80}")
    print(f"Q{i+1} [{dim}] [{diff}]")
    print(f"Q: {q}")
    print(f"{'-'*40}")
    print(f"BL ({len(bl_ans)} chars):")
    print(bl_ans[:2000])
    print(f"{'-'*40}")
    print(f"LS ({len(ls_ans)} chars):")
    print(ls_ans[:2000])
