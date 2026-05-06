# -*- coding: utf-8 -*-
with open(r'E:\Study\Dapper_Coding\learning_agent.py', 'rb') as f:
    data = f.read()

# Replace bytes 16243 to 17629 (the corrupted second system_prompt block)
start = 16243
end = 17629  # inclusive

# Verify we're replacing the right thing
print(f'Old block [{start}:{end}]:', repr(data[start:start+60]))
print(f'Block after end: {repr(data[end:end+30])}')

# Build new system_prompt
lines = [
    '你是一个专业、详尽的信息解读专家。请根据搜索结果为用户做出全面、准确、有深度的回答。\n\n',
    '回答要求：\n',
    '1. 先给出核心且完整的答案（结论先行）\n',
    '2. 然后提供详细的解释说明，包含背景、原理、例子等\n',
    '3. 如果涉及技术内容，请包含代码示例、步骤或图表描述\n',
    '4. 结构化呈现：使用分点、编号、表格等方式让信息清晰\n',
    '5. 引用搜索结果中的具体数据和来源\n',
    '6. 如果搜索结果中没有相关信息，直接说"目前没有找到相关资料"，不要编造\n',
    '7. 不要添加任何标签，如"AI总结"、"内容来源"等\n',
    '8. 回答要有足够的深度——不要只给结论，要给出完整的推导和分析过程\n',
    '9. 【技术/编程类】必须包含：代码示例 + 运行结果说明 + 复杂度分析\n',
    '10. 【分析/推理类】必须包含：推导步骤 + 公式 + 验证方法\n',
    '11. 【实用/操作类】必须包含：具体步骤 + 注意事项 + 常见误区',
]
full_text = ''.join(lines)
new_block = b'                system_prompt = (\n                    "' + full_text.encode('utf-8') + b'"\n                )'

new_data = data[:start] + new_block + data[end+1:]
with open(r'E:\Study\Dapper_Coding\learning_agent.py', 'wb') as f:
    f.write(new_data)
print(f'Done. New size: {len(new_data)} vs old: {len(data)}')
