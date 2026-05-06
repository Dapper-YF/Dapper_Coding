# -*- coding: utf-8 -*-
import json

with open(r'E:\Study\Dapper_Coding\eval_ls_answers.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

questions = []
for item in data:
    questions.append({
        "id": f"Q{item['index']}",
        "question": item["question"],
        "difficulty": item.get("difficulty", "medium"),
        "dimension": item.get("dimension", "general"),
        "expected_tags": item.get("expected_tags", [])
    })
    print(f"Q{item['index']}: {item['question'][:60]} [{item.get('difficulty','?')}] [{item.get('dimension','?')}]")

print(f"\nTotal: {len(questions)} questions")

# Write question bank
with open(r'E:\Study\Dapper_Coding\question_bank.json', 'w', encoding='utf-8') as f:
    json.dump({"version": "1.0", "last_updated": "2026-04-30", "questions": questions}, f, ensure_ascii=False, indent=2)
print("Written to question_bank.json")
