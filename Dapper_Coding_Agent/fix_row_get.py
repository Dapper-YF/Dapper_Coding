# -*- coding: utf-8 -*-
with open(r'E:\Study\Dapper_Coding\dapper_coding_agent.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix row.get() to row[] for sqlite3.Row
old_code = '''        for row in rows:
            users.append({
                "user_id": row["user_id"],
                "关注领域": row.get("关注领域") or "",
                "难度偏好": row.get("难度偏好") or "入门",
                "digest_enabled": bool(row.get("digest_enabled", 1)),
                "created_at": row.get("created_at") or "",
            })'''

new_code = '''        for row in rows:
            users.append({
                "user_id": row["user_id"],
                "关注领域": row["关注领域"] if row["关注领域"] else "",
                "难度偏好": row["难度偏好"] if row["难度偏好"] else "入门",
                "digest_enabled": bool(row["digest_enabled"]) if row["digest_enabled"] else False,
                "created_at": row["created_at"] if row["created_at"] else "",
            })'''

if old_code in content:
    content = content.replace(old_code, new_code)
    print("Fixed row.get() issue")
else:
    print("Pattern not found")

with open(r'E:\Study\Dapper_Coding\dapper_coding_agent.py', 'w', encoding='utf-8') as f:
    f.write(content)

import py_compile
try:
    py_compile.compile(r'E:\Study\Dapper_Coding\dapper_coding_agent.py', doraise=True)
    print("Syntax OK")
except Exception as e:
    print("Syntax error:", e)
