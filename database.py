"""
database.py — PostgreSQL via Railway (No data loss on re-deploy)
"""

import os
import psycopg2
from contextlib import contextmanager
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

# Get Railway's PostgreSQL URL
DATABASE_URL = os.getenv("postgresql://postgres:GWZeFFQYmDxBdMRxnncNYYEBOjnQgziS@postgres.railway.internal:5432/railway")  # Railway sets this automatically!

@contextmanager
def get_conn():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
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
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id SERIAL PRIMARY KEY,
                place_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                category TEXT,
                address TEXT,
                phone TEXT,
                website TEXT,
                rating REAL,
                status TEXT DEFAULT 'Not Contacted',
                notes TEXT DEFAULT '',
                last_contacted TEXT DEFAULT '',
                follow_up_date TEXT DEFAULT '',
                channel TEXT DEFAULT '',
                replied TEXT DEFAULT '',
                instagram TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        conn.commit()

def insert_lead(lead: dict):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO leads 
                (place_id, name, category, address, phone, website, rating)
            VALUES
                (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (place_id) DO NOTHING
        """, (
            lead.get('place_id'),
            lead.get('name'),
            lead.get('category'),
            lead.get('address'),
            lead.get('phone'),
            lead.get('website'),
            lead.get('rating')
        ))
        conn.commit()

def lead_exists(place_id: str) -> bool:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM leads WHERE place_id = %s", (place_id,))
        return cur.fetchone() is not None

def fetch_all_leads() -> list[dict]:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM leads ORDER BY created_at DESC")
        return [dict(row) for row in cur.fetchall()]

def fetch_lead(lead_id: int) -> dict:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM leads WHERE id = %s", (lead_id,))
        row = cur.fetchone()
        return dict(row) if row else {}

def update_field(lead_id: int, field: str, value: str):
    allowed = {"status", "notes", "last_contacted", "follow_up_date",
               "channel", "replied", "instagram", "name", "phone", "website"}
    if field not in allowed:
        raise ValueError(f"Field '{field}' not allowed")
    
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(f"UPDATE leads SET {field} = %s WHERE id = %s", (value, lead_id))
        if field == "status" and value == "Contacted":
            cur.execute(
                "UPDATE leads SET last_contacted = CURRENT_DATE WHERE id = %s AND last_contacted = ''",
                (lead_id,)
            )
        conn.commit()

def delete_lead(lead_id: int):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM leads WHERE id = %s", (lead_id,))
        conn.commit()

def get_stats() -> dict:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM leads")
        total = cur.fetchone()['count']
        
        cur.execute("SELECT COUNT(*) FROM leads WHERE status = 'Contacted'")
        contacted = cur.fetchone()['count']
        
        cur.execute("SELECT COUNT(*) FROM leads WHERE replied = 'Yes'")
        replied = cur.fetchone()['count']
        
        cur.execute("""
            SELECT COUNT(*) FROM leads
            WHERE follow_up_date != '' AND follow_up_date <= CURRENT_DATE
            AND status != 'Converted'
        """)
        due = cur.fetchone()['count']
        
        cur.execute("""
            SELECT channel, COUNT(*) as cnt FROM leads
            WHERE channel != '' GROUP BY channel ORDER BY cnt DESC
        """)
        by_channel = cur.fetchall()
    
    return {
        "total": total,
        "contacted": contacted,
        "uncontacted": total - contacted,
        "replied": replied,
        "due": due,
        "by_channel": [dict(r) for r in by_channel],
        "reply_rate": round(replied / contacted * 100) if contacted else 0,
    }

def fetch_daily_queue(limit: int = 10) -> list[dict]:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM leads
            WHERE status = 'Not Contacted'
            ORDER BY
                CASE WHEN website != '' THEN 0 ELSE 1 END,
                CASE WHEN phone != '' THEN 0 ELSE 1 END,
                rating DESC NULLS LAST
            LIMIT %s
        """, (limit,))
        return [dict(row) for row in cur.fetchall()]

def fetch_due_followups() -> list[dict]:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM leads
            WHERE follow_up_date != '' AND follow_up_date <= CURRENT_DATE
            ORDER BY follow_up_date ASC
        """)
        return [dict(row) for row in cur.fetchall()]
