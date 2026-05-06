# -*- coding: utf-8 -*-
import sqlite3
conn = sqlite3.connect('/opt/Dapper_Coding_Agent/dapper_memory.db')
conn.execute('DELETE FROM digest_history')
conn.commit()
print('digest_history cleared')
