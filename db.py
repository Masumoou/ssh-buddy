"""
db.py — SQLite backend for SSH Buddy
Stores: alias, ip, username, port, tags, notes
"""

import sqlite3
from pathlib import Path

DB_PATH = Path.home() / ".ssh_buddy" / "servers.db"


def init_db():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS servers (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            alias      TEXT UNIQUE NOT NULL,
            ip         TEXT NOT NULL,
            username   TEXT NOT NULL,
            port       INTEGER DEFAULT 22,
            tags       TEXT    DEFAULT '',
            notes      TEXT    DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            use_key    BOOLEAN DEFAULT 0
        )
    """)
    
    # Migration for existing databases
    try:
        c.execute("ALTER TABLE servers ADD COLUMN use_key BOOLEAN DEFAULT 0")
    except sqlite3.OperationalError:
        pass
        
    conn.commit()
    conn.close()


def add_server(alias, ip, username, port=22, tags="", notes="", use_key=0):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO servers (alias, ip, username, port, tags, notes, use_key) VALUES (?,?,?,?,?,?,?)",
            (alias, ip, username, port, tags, notes, use_key),
        )
        conn.commit()
        return True, "Server added successfully"
    except sqlite3.IntegrityError:
        return False, f"Alias '{alias}' already exists. Use a different alias."
    finally:
        conn.close()


def update_server(alias, **kwargs):
    if not kwargs:
        return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    fields = ", ".join([f"{k}=?" for k in kwargs])
    values = list(kwargs.values()) + [alias]
    c.execute(f"UPDATE servers SET {fields} WHERE alias=?", values)
    conn.commit()
    conn.close()


def delete_server(alias):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM servers WHERE alias=?", (alias,))
    affected = c.rowcount
    conn.commit()
    conn.close()
    return affected > 0


def get_all_servers():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM servers ORDER BY alias COLLATE NOCASE")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_server(alias):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM servers WHERE alias=?", (alias,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def search_servers(query):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    q = f"%{query}%"
    c.execute(
        """SELECT * FROM servers
           WHERE alias LIKE ? OR ip LIKE ? OR username LIKE ?
              OR tags LIKE ? OR notes LIKE ?
           ORDER BY alias COLLATE NOCASE""",
        (q, q, q, q, q),
    )
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]
