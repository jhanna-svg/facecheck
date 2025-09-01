#!/usr/bin/env python3
import sqlite3
import os
from werkzeug.security import generate_password_hash

DB = os.path.join(os.path.dirname(os.path.dirname(__file__)), "facerecognition.db")

if not os.path.exists(DB):
    print("Database not found at:", DB)
    raise SystemExit(1)

conn = sqlite3.connect(DB)
c = conn.cursor()

# Check if column exists
c.execute("PRAGMA table_info(user)")
cols = [row[1] for row in c.fetchall()]
if 'password_hash' not in cols:
    print("Adding password_hash column...")
    c.execute("ALTER TABLE user ADD COLUMN password_hash TEXT")
    conn.commit()
else:
    print("password_hash column already exists.")

# Migrate plaintext passwords into password_hash where needed
c.execute("SELECT id, password, password_hash FROM user")
rows = c.fetchall()
migrated = 0
for id_, pwd, pwd_hash in rows:
    if (pwd or "") and not (pwd_hash or ""):
        new_hash = generate_password_hash(pwd)
        c.execute("UPDATE user SET password_hash = ? WHERE id = ?", (new_hash, id_))
        migrated += 1

conn.commit()
conn.close()
print(f"Migration complete. Passwords hashed for {migrated} users.")
