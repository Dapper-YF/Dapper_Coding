import json

f1 = open(r'E:\Study\Dapper_Coding\eval_baseline_answers.json', 'r', encoding='utf-8')
f2 = open(r'E:\Study\Dapper_Coding\eval_ls_answers.json', 'r', encoding='utf-8')
bl = json.load(f1)
ls = json.load(f2)
f1.close()
f2.close()

print(f"Total questions: {len(bl)}")
for i in range(len(bl)):
    q = bl[i]['question']
    bl_ans = bl[i]['answer']
    ls_ans = ls[i]['answer']
    print(f"Q{i+1}: len_bl={len(bl_ans)}, len_ls={len(ls_ans)}, q={q[:50]}")
