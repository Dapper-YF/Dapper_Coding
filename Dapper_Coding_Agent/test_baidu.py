# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import os, importlib.util

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

# 测试 Baidu 搜索
print('=== 测试 Baidu 搜索: 快速排序算法原理 ===')
result = la._baidu_search('快速排序算法原理', num_results=5, timeout=10)
print(f'结果长度: {len(result)} 字')
print('前800字:')
print(result[:800] if result else 'EMPTY')

print()
print('=== 测试 Baidu 搜索: Git rebase merge 区别 ===')
result2 = la._baidu_search('Git rebase merge 区别 适用场景', num_results=5, timeout=10)
print(f'结果长度: {len(result2)} 字')
print('前800字:')
print(result2[:800] if result2 else 'EMPTY')
