import os
import sqlite3

DB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "instance", "users.db")
)
print("DB:", DB_PATH)
con = sqlite3.connect(DB_PATH)
cur = con.cursor()
cur.execute("PRAGMA table_info(usuarios)")
cols = [r[1] for r in cur.fetchall()]
print("Columns:", cols)
if "color" not in cols:
    print("Adding color column...")
    cur.execute("ALTER TABLE usuarios ADD COLUMN color VARCHAR(20)")
    con.commit()
    print("Column added.")
else:
    print("Color column already present")
con.close()
