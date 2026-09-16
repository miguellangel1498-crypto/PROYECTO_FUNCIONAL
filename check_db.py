import sqlite3
conn = sqlite3.connect('instance/growth_horizon.db')
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
print('Tables:', c.fetchall())
c.execute('PRAGMA table_info(auditoria)')
print('Auditoria columns:', c.fetchall())
conn.close()