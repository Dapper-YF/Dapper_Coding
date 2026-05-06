import sqlite3
conn = sqlite3.connect('E:\\Study\\Dapper_Coding\\dapper_memory.db')
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print(tables)

# Show schema for each table
for t in tables:
    cur.execute(f"PRAGMA table_info({t})")
    cols = [r[1] for r in cur.fetchall()]
    print(f"\n{t}: {cols}")
