# -*- coding: utf-8 -*-
import json, os

proj_mem = r'C:\Users\Dapper\.openclaw\projects\Dapper_Coding\PROJECT_MEMORY.md'

with open(proj_mem, 'r', encoding='utf-8') as f:
    content = f.read()

if '## 训练基础设施' in content:
    print('Already exists')
else:
    append = '''

---

## 训练基础设施（2026-04-30 新增）

### 题库
- 位置：`E:\\Study\\Dapper_Coding\\question_bank.json`
- 格式：JSON，字段包括 id/question/expected_tags/difficulty/category
- 当前：33题，覆盖 tech/science/analysis/practical/explain 五类
- 维护：Scout QA Monitor 负责追加新题目（去重）

### 本地快速测试脚本
- 位置：`E:\\Study\\Dapper_Coding\\local_eval.py`
- 用法：`python local_eval.py`（测P0题目）/ `python local_eval.py Q1 Q7`（测指定题）
- 原理：直接 import learning_agent.py，绕过失飞书 Bot，直接测核心逻辑
- 输出：字数、代码标记、步骤标记、例子标记

### Scout QA Monitor（Supervisor 子智能体）
- 职责：周期性检查、新题目入库、质量预警、训练记录维护
- 触发：Architect 主动发消息驱动，或每周自动

### 训练轮次记录

| 轮次 | 日期 | LS均分 | BL均分 | P0数 | 主要修复 | 状态 |
|------|------|--------|--------|------|---------|------|
| 第1轮 | 2026-04-30 | 3.69 | 3.75 | 5 | 搜索清洗/max_tokens/深度Prompt | ✅ |
| 第2轮 | 2026-04-30 | 待测 | - | - | num_results扩展/11条规则 | 复测中 |
'''
    content += append
    with open(proj_mem, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'Updated {proj_mem}')

# Also update workspace copy
ws_mem = r'E:\Study\Dapper_Coding\.project_memory\PROJECT_MEMORY.md'
with open(ws_mem, 'r', encoding='utf-8', errors='ignore') as f:
    ws_content = f.read()

if '## 训练基础设施' not in ws_content:
    ws_content += append
    with open(ws_mem, 'w', encoding='utf-8') as f:
        f.write(ws_content)
    print(f'Updated workspace copy')
