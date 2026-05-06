# -*- coding: utf-8 -*-
# 读取现有测试题，构建题库
# 题库格式：JSON，每题含 id/question/expected_tags/difficulty/category

questions = [
    # 技术类
    {"id": "Q1", "question": "光合作用是怎么进行的？", "expected_tags": ["光合作用", "叶绿体", "光反应", "暗反应"], "difficulty": "medium", "category": "science"},
    {"id": "Q5", "question": "什么是RESTful API？它和普通API有什么区别？", "expected_tags": ["REST", "API", "HTTP方法", "资源"], "difficulty": "medium", "category": "tech"},
    {"id": "Q6", "question": "Python里list和tuple有什么区别？什么时候该用哪个？", "expected_tags": ["list", "tuple", "不可变", "可变"], "difficulty": "easy", "category": "tech"},
    {"id": "Q7", "question": "快速排序是怎么实现的？能写个代码吗？", "expected_tags": ["快速排序", "分治", "递归", "quicksort"], "difficulty": "hard", "category": "tech"},
    {"id": "Q9", "question": "Git rebase和merge有什么区别？各自适用什么场景？", "expected_tags": ["Git", "rebase", "merge", "版本控制"], "difficulty": "medium", "category": "tech"},
    # 分析/推理类
    {"id": "Q2", "question": "为什么天是蓝色的？", "expected_tags": ["瑞利散射", "蓝光", "大气层"], "difficulty": "medium", "category": "science"},
    {"id": "Q3", "question": "什么是薛定谔方程？", "expected_tags": ["量子力学", "波函数", "不确定性"], "difficulty": "hard", "category": "science"},
    {"id": "Q4", "question": "相对论和时间膨胀是什么关系？", "expected_tags": ["相对论", "时间膨胀", "光速"], "difficulty": "hard", "category": "science"},
    {"id": "Q8", "question": "从经济学角度分析，为什么手机越来越便宜而房子越来越贵？", "expected_tags": ["供需", "通货膨胀", "摩尔定律", "房产"], "difficulty": "hard", "category": "analysis"},
    {"id": "Q10", "question": "为什么中国的大江大河都是向东流？", "expected_tags": ["地形", "地势", "西高东低", "水往低处流"], "difficulty": "easy", "category": "science"},
    # 实用/操作类
    {"id": "Q11", "question": "如何在Excel里实现自动筛选并高亮重复项？", "expected_tags": ["Excel", "条件格式", "筛选", "重复"], "difficulty": "easy", "category": "practical"},
    {"id": "Q12", "question": "怎样给父母解释什么是区块链？", "expected_tags": ["区块链", "去中心化", "分布式", "比特币"], "difficulty": "medium", "category": "explain"},
]

import json, os
out_path = r'E:\Study\Dapper_Coding\question_bank.json'
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump({"version": "1.0", "last_updated": "2026-04-30", "questions": questions}, f, ensure_ascii=False, indent=2)
print(f'Written {len(questions)} questions to {out_path}')
