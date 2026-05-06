# -*- coding: utf-8 -*-
with open(r'E:\Study\Dapper_Coding\memory.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Check if ALTER TABLE already added
if 'ALTER TABLE user_profiles ADD COLUMN learning_level' not in content:
    # Find the position after CREATE TABLE IF NOT EXISTS user_profiles
    marker = 'conn.execute("""\n                CREATE TABLE IF NOT EXISTS user_profiles (\n                    user_id TEXT PRIMARY KEY,'
    
    if marker in content:
        insert_pos = content.find(marker) + len(marker)
        
        alter_code = '''
            
            # 补充新列（如果不存在）- 教学智能体需要的字段
            try:
                conn.execute("ALTER TABLE user_profiles ADD COLUMN learning_level TEXT DEFAULT 'intermediate'")
            except sqlite3.OperationalError:
                pass  # 列已存在
            
            try:
                conn.execute("ALTER TABLE user_profiles ADD COLUMN interests TEXT DEFAULT '[]'")
            except sqlite3.OperationalError:
                pass  # 列已存在
            
            try:
                conn.execute("ALTER TABLE user_profiles ADD COLUMN learning_history TEXT DEFAULT '[]'")
            except sqlite3.OperationalError:
                pass  # 列已存在
'''
        content = content[:insert_pos] + alter_code + content[insert_pos:]
        print("Added ALTER TABLE logic")
    else:
        print("Marker not found:", repr(marker[:50]))
else:
    print("ALTER TABLE already exists")

# Add update_user_interests function at the end
if 'def update_user_interests' not in content:
    new_func = '''

# ============================================================
# 用户兴趣更新（反思机制）
# ============================================================

def update_user_interests(user_id: str, topic: str) -> bool:
    """更新用户感兴趣的话题"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            row = conn.execute(
                "SELECT interests FROM user_profiles WHERE user_id=?",
                (user_id,)
            ).fetchone()
            
            if not row:
                return False
            
            try:
                interests = json.loads(row[0]) if row[0] else []
            except json.JSONDecodeError:
                interests = []
            
            # 提取关键词（简化版）
            keywords = extract_keywords_from_topic(topic)
            for kw in keywords:
                if kw not in interests:
                    interests.append(kw)
            
            interests = interests[-50:]
            
            conn.execute(
                "UPDATE user_profiles SET interests=? WHERE user_id=?",
                (json.dumps(interests, ensure_ascii=False), user_id)
            )
            conn.commit()
            return True
            
    except Exception as exc:
        logging.error("update_user_interests failed: %s", exc)
        return False


def extract_keywords_from_topic(topic: str) -> list:
    """从话题中提取关键词"""
    import re
    cleaned = re.sub(r'[^\\w\\s]', ' ', topic.lower())
    words = cleaned.split()
    
    tech_keywords = [
        'python', 'javascript', 'java', 'rust', 'go', 'typescript',
        'machine-learning', 'deep-learning', 'nlp', 'cv', 'ai', 'ml', 'dl',
        'web', 'frontend', 'backend', 'api', 'database',
        'docker', 'kubernetes', 'git', 'linux',
        'react', 'vue', 'nodejs', 'flask', 'django',
        'tensorflow', 'pytorch', 'pandas', 'numpy',
    ]
    
    keywords = []
    for word in words:
        for kw in tech_keywords:
            if kw in word or word in kw:
                keywords.append(kw)
    
    return list(dict.fromkeys(keywords))[:10]
'''
    content = content + new_func
    print("Added update_user_interests function")
else:
    print("update_user_interests already exists")

with open(r'E:\Study\Dapper_Coding\memory.py', 'w', encoding='utf-8') as f:
    f.write(content)

import py_compile
try:
    py_compile.compile(r'E:\Study\Dapper_Coding\memory.py', doraise=True)
    print("Syntax OK")
except Exception as e:
    print("Syntax error:", e)
