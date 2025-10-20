# core/db.py
import os
import sqlite3
from typing import Optional, Tuple, Dict, Any

DB_PATH = os.getenv("SUPPORT_DB_PATH", "data/support.db")
_CONN: Optional[sqlite3.Connection] = None

def get_conn() -> sqlite3.Connection:
    """Singleton SQLite connection with row dicts and thread-safe settings for Streamlit."""
    global _CONN
    if _CONN is None:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        _CONN = sqlite3.connect(DB_PATH, check_same_thread=False)
        _CONN.row_factory = sqlite3.Row
        _init_db(_CONN)
    return _CONN

def init_db() -> sqlite3.Connection:
    """Backwards-compatible: ensure DB exists and return a live connection."""
    return get_conn()

def _init_db(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    # support_tickets table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS support_tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id TEXT UNIQUE,
        customer_name TEXT,
        description TEXT,
        status TEXT DEFAULT 'Open',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    # app_logs table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS app_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        level TEXT,
        agent TEXT,
        event TEXT,
        details TEXT
    )
    """)
    conn.commit()

def _ensure_conn(conn: Optional[sqlite3.Connection]) -> sqlite3.Connection:
    if conn is None or not hasattr(conn, "cursor"):
        return get_conn()
    return conn

def insert_ticket(conn: Optional[sqlite3.Connection], *, ticket_id: str, customer_name: str, description: str, status: str = "Open") -> None:
    conn = _ensure_conn(conn)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO support_tickets (ticket_id, customer_name, description, status) VALUES (?, ?, ?, ?)",
        (ticket_id, customer_name, description, status),
    )
    conn.commit()

def get_ticket(conn: Optional[sqlite3.Connection], ticket_id: str) -> Optional[Dict[str, Any]]:
    conn = _ensure_conn(conn)
    cur = conn.cursor()
    cur.execute("SELECT * FROM support_tickets WHERE ticket_id = ?", (ticket_id,))
    row = cur.fetchone()
    return dict(row) if row else None

def list_tickets(conn: Optional[sqlite3.Connection], limit: int = 200):
    conn = _ensure_conn(conn)
    cur = conn.cursor()
    cur.execute("SELECT * FROM support_tickets ORDER BY created_at DESC LIMIT ?", (limit,))
    return [dict(r) for r in cur.fetchall()]

def log_event(conn: Optional[sqlite3.Connection], *, level: str, agent: str, event: str, details: Dict[str, Any]):
    import json
    conn = _ensure_conn(conn)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO app_logs (level, agent, event, details) VALUES (?, ?, ?, ?)",
        (level, agent, event, json.dumps(details or {})),
    )
    conn.commit()

def list_logs(conn: Optional[sqlite3.Connection], limit: int = 200):
    conn = _ensure_conn(conn)
    cur = conn.cursor()
    cur.execute("SELECT * FROM app_logs ORDER BY ts DESC LIMIT ?", (limit,))
    return [dict(r) for r in cur.fetchall()]

def find_open_ticket_by_customer(conn: Optional[sqlite3.Connection], customer_name: str) -> Optional[Tuple[str, str]]:
    """
    Return the most recent open/in-progress ticket for a customer name as (ticket_id, status),
    or None if none exists.
    """
    if not (customer_name or "").strip():
        return None
    conn = _ensure_conn(conn)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT ticket_id, status
        FROM support_tickets
        WHERE customer_name = ?
          AND status IN ('Open', 'In-Progress')
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (customer_name,),
    )
    row = cur.fetchone()
    return (row["ticket_id"], row["status"]) if row else None
