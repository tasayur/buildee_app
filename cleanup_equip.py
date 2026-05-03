import sqlite3, os
db = os.path.join(os.path.dirname(__file__), 'buildee.db')
conn = sqlite3.connect(db)
cur = conn.execute("DELETE FROM equipment_reservations WHERE equipment IN ('高所作業車','ゲート（北）')")
conn.commit()
print(f'削除件数: {cur.rowcount}件')
conn.close()
