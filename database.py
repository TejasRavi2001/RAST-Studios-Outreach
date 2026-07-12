"""
database.py — SQLite helpers for RAST Studios lead system.
Safe migration: adds new columns without touching existing data.
"""

import sqlite3
from contextlib import contextmanager

DB_PATH = "leads.db"

@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                place_id        TEXT    UNIQUE NOT NULL,
                name            TEXT    NOT NULL,
                category        TEXT,
                address         TEXT,
                phone           TEXT,
                website         TEXT,
                rating          REAL,
                status          TEXT    DEFAULT 'Not Contacted',
                notes           TEXT    DEFAULT '',
                last_contacted  TEXT    DEFAULT '',
                follow_up_date  TEXT    DEFAULT '',
                channel         TEXT    DEFAULT '',
                replied         TEXT    DEFAULT '',
                instagram       TEXT    DEFAULT '',
                created_at      TEXT    DEFAULT (datetime('now'))
            )
        """)

        # Safe migration — add columns if they don't exist
        existing = {r["name"] for r in conn.execute("PRAGMA table_info(leads)").fetchall()}
        migrations = {
            "last_contacted": "TEXT DEFAULT ''",
            "follow_up_date": "TEXT DEFAULT ''",
            "channel":        "TEXT DEFAULT ''",
            "replied":        "TEXT DEFAULT ''",
            "instagram":      "TEXT DEFAULT ''",
        }
        for col, typedef in migrations.items():
            if col not in existing:
                conn.execute(f"ALTER TABLE leads ADD COLUMN {col} {typedef}")

def insert_lead(lead: dict):
    with get_conn() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO leads
                (place_id, name, category, address, phone, website, rating)
            VALUES
                (:place_id, :name, :category, :address, :phone, :website, :rating)
        """, lead)

def lead_exists(place_id: str) -> bool:
    with get_conn() as conn:
        row = conn.execute("SELECT 1 FROM leads WHERE place_id = ?", (place_id,)).fetchone()
        return row is not None

def fetch_all_leads() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM leads ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]

def fetch_lead(lead_id: int) -> dict:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
        return dict(row) if row else {}

def update_field(lead_id: int, field: str, value: str):
    allowed = {"status", "notes", "last_contacted", "follow_up_date",
               "channel", "replied", "instagram", "name", "phone", "website"}
    if field not in allowed:
        raise ValueError(f"Field '{field}' not allowed")
    with get_conn() as conn:
        conn.execute(f"UPDATE leads SET {field} = ? WHERE id = ?", (value, lead_id))
        # Auto-stamp last_contacted when marking as Contacted
        if field == "status" and value == "Contacted":
            conn.execute(
                "UPDATE leads SET last_contacted = date('now') WHERE id = ? AND last_contacted = ''",
                (lead_id,)
            )

def delete_lead(lead_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM leads WHERE id = ?", (lead_id,))

def get_stats() -> dict:
    with get_conn() as conn:
        total      = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
        contacted  = conn.execute("SELECT COUNT(*) FROM leads WHERE status = 'Contacted'").fetchone()[0]
        replied    = conn.execute("SELECT COUNT(*) FROM leads WHERE replied = 'Yes'").fetchone()[0]
        due        = conn.execute("""
            SELECT COUNT(*) FROM leads
            WHERE follow_up_date != '' AND follow_up_date <= date('now')
            AND status != 'Converted'
        """).fetchone()[0]
        by_channel = conn.execute("""
            SELECT channel, COUNT(*) as cnt FROM leads
            WHERE channel != '' GROUP BY channel ORDER BY cnt DESC
        """).fetchall()
    return {
        "total":       total,
        "contacted":   contacted,
        "uncontacted": total - contacted,
        "replied":     replied,
        "due":         due,
        "by_channel":  [dict(r) for r in by_channel],
        "reply_rate":  round(replied / contacted * 100) if contacted else 0,
    }

def fetch_daily_queue(limit: int = 10) -> list[dict]:
    """Top leads to contact today — uncontacted, sorted by rating desc."""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT * FROM leads
            WHERE status = 'Not Contacted'
            ORDER BY
                CASE WHEN website != '' THEN 0 ELSE 1 END,
                CASE WHEN phone != ''   THEN 0 ELSE 1 END,
                rating DESC NULLS LAST
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]

def fetch_due_followups() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT * FROM leads
            WHERE follow_up_date != '' AND follow_up_date <= date('now')
            ORDER BY follow_up_date ASC
        """).fetchall()
        return [dict(r) for r in rows]
