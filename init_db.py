import sqlite3

conn = sqlite3.connect("harnect.db")
conn.execute("""
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    content TEXT
);
""")
conn.close()
