# -*- coding: utf-8 -*-
"""
Learning Scout 本地快速测试脚本
用途：直接调用 learning_agent.py 测试回答质量（绕过失飞书 Bot）
用法：python local_eval.py [QID ...]
      python local_eval.py          # 测试全部 P0 题目（Q1 Q5 Q6 Q7 Q9）
      python local_eval.py Q1 Q7   # 测试指定题目
"""
import json, sys, importlib.util, os

# ====== 加载 .env 环境变量 ======
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(r'E:\Study\Dapper_Coding', '.env'))
except ImportError:
    # 如果没有 python-dotenv，手动解析 .env 文件
    env_path = os.path.join(r'E:\Study\Dapper_Coding', '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, _, value = line.partition('=')
                    os.environ[key.strip()] = value.strip().strip('"').strip("'")

# ====== 加载 learning_agent.py ======
spec = importlib.util.spec_from_file_location("la", r'E:\Study\Dapper_Coding\learning_agent.py')
la = importlib.util.module_from_spec(spec)
spec.loader.exec_module(la)

# ====== 加载题库 ======
with open(r'E:\Study\Dapper_Coding\question_bank.json', 'r', encoding='utf-8') as f:
    qbank = json.load(f)

# ====== 测试函数 ======
def test_question(q_obj, user_id="local_test", channel="local"):
    qid = q_obj["id"]
    question = q_obj["question"]
    expected = q_obj.get("expected_tags", [])

    print(f"\n{'='*60}")
    print(f"[{qid}] {question}")
    print(f"难度: {q_obj['difficulty']} | 类型: {q_obj['category']}")
    print(f"期望关键词: {', '.join(expected) if expected else '未标注'}")
    print('-' * 60)

    try:
        answer = la.process_user_message(user_id, channel, question)
    except Exception as e:
        answer = f"[ERROR] {e}"

    # 输出（截断到800字）
    if len(answer) > 800:
        print(f"回答（截断800字）:\n{answer[:800]}...")
    else:
        print(f"回答:\n{answer}")

    # 质量检查
    length = len(answer)
    has_code = any(x in answer for x in ['```', 'def ', 'class ', 'import ', 'for ', 'if '])
    has_steps = any(x in answer for x in ['步骤', '第一步', '第二', '1.', '①', '②'])
    has_examples = any(x in answer for x in ['例如', '比如', '例子', '示例', 'e.g.'])
    has_depth = length > 200

    print('-' * 40)
    checks = {
        "字数": f"{length}",
        "代码": "Y" if has_code else "N",
        "步骤": "Y" if has_steps else "N",
        "例子": "Y" if has_examples else "N",
        "深度": "Y" if has_depth else "N",
    }
    for k, v in checks.items():
        print(f"  {k}: {v}")

    # 问题标记
    issues = []
    if length < 100:
        issues.append("回答过短")
    if not has_code and q_obj['category'] == 'tech':
        issues.append("技术题缺少代码")
    if not has_steps and q_obj['difficulty'] == 'hard':
        issues.append("难题缺少步骤拆解")
    if not has_depth:
        issues.append("深度不足")

    if issues:
        print("  ! " + " | ".join(issues))

    return {
        "id": qid, "question": question, "answer": answer,
        "length": length, "has_code": has_code, "has_steps": has_steps,
        "has_examples": has_examples, "issues": issues
    }

# ====== 主逻辑 ======
target_ids = sys.argv[1:] if len(sys.argv) > 1 else ["Q1", "Q5", "Q6", "Q7", "Q9"]

print(f"Learning Scout 本地快速测试")
print(f"题库: question_bank.json (共 {qbank['total']} 题)")
print(f"测试题目: {target_ids}")

questions = [q for q in qbank["questions"] if q["id"] in target_ids]
missing = set(target_ids) - {q["id"] for q in questions}
if missing:
    print(f"! 找不到: {missing}")

results = []
for q in questions:
    r = test_question(q)
    results.append(r)

# 汇总
print(f"\n{'='*60}")
print("测试汇总")
print(f"{'='*60}")
for r in results:
    status = "OK" if not r["issues"] else "WARN:" + "|".join(r["issues"][:2])
    print(f"  {r['id']}: len={r['length']:4d} code={'Y' if r['has_code'] else 'N'} steps={'Y' if r['has_steps'] else 'N'} {status}")

avg_len = sum(r["length"] for r in results) / len(results) if results else 0
print(f"\n平均字数: {avg_len:.0f}")
print(f"P0 题目参考: Q1/Q5/Q6/Q7/Q9")
print(f"对比历史: eval_report.xlsx 第1轮 LS均分=3.69")
