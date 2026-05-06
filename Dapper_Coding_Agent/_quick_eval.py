# -*- coding: utf-8 -*-
import json, importlib.util, sys

# Load learning_agent.py
LA_PATH = r'E:\Study\Dapper_Coding\learning_agent.py'
spec = importlib.util.spec_from_file_location("learning_agent", LA_PATH)
la = importlib.util.module_from_spec(spec)
spec.loader.exec_module(la)

# Load question bank
with open(r'E:\Study\Dapper_Coding\question_bank.json', 'r', encoding='utf-8') as f:
    qbank = json.load(f)

# Test P0 questions
target_ids = ["Q1", "Q5", "Q6", "Q7", "Q9"]
questions = [q for q in qbank["questions"] if q["id"] in target_ids]

results = []
for q in questions:
    qid = q["id"]
    question = q["question"]
    expected = q.get("expected_tags", [])
    print(f"\n{'='*60}")
    print(f"[{qid}] {question}")
    print(f"期望关键词: {', '.join(expected)}")
    print('-' * 60)
    try:
        answer = la.process_user_message("local_test_user", "local_eval", question)
    except Exception as e:
        answer = f"[ERROR] {e}"
        print(answer)
        continue
    if len(answer) > 600:
        print(f"回答（截断到600字）: {answer[:600]}...")
    else:
        print(f"回答: {answer}")
    length = len(answer)
    has_code = '```' in answer or 'def ' in answer or 'class ' in answer or 'import ' in answer
    has_steps = any(kw in answer for kw in ['步骤', '第一步', '1.', '①'])
    has_examples = any(kw in answer for kw in ['例如', '比如', 'example', '例子'])
    print('-' * 40)
    print(f"字数={length} | 代码={'Y' if has_code else 'N'} | 步骤={'Y' if has_steps else 'N'} | 例子={'Y' if has_examples else 'N'}")
    if length < 100:
        print("WARN: 回答过短")
    results.append({"id": qid, "length": length, "has_code": has_code, "has_steps": has_steps, "has_examples": has_examples})

avg_len = sum(r["length"] for r in results) / len(results) if results else 0
print(f"\n平均字数: {avg_len:.0f}")
