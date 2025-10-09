# core/db.py
import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any, List

DB_PATH = Path("support.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS support_tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_no TEXT UNIQUE NOT NULL,
    customer_name TEXT,
    description TEXT,
    status TEXT DEFAULT 'Open',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS app_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    level TEXT,
    agent TEXT,
    event TEXT,
    details TEXT
);
"""

def get_conn() -> sqlite3.Connection:
    """Get SQLite connection with WAL mode."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db() -> None:
    """Initialize tables if they don’t exist."""
    conn = get_conn()
    with conn:
        conn.executescript(SCHEMA)
    conn.close()

def insert_ticket(ticket_no: str, customer_name: Optional[str], description: str, status: str = "Open") -> None:
    """Insert a new support ticket."""
    conn = get_conn()
    with conn:
        conn.execute(
            "INSERT INTO support_tickets (ticket_no, customer_name, description, status) VALUES (?, ?, ?, ?)",
            (ticket_no, customer_name, description, status),
        )
    conn.close()

def update_ticket_status(ticket_no: str, status: str) -> None:
    """Update ticket status."""
    conn = get_conn()
    with conn:
        conn.execute(
            "UPDATE support_tickets SET status = ? WHERE ticket_no = ?",
            (status, ticket_no),
        )
    conn.close()

def get_ticket(ticket_no: str) -> Optional[Dict[str, Any]]:
    """Retrieve one ticket by ticket number."""
    conn = get_conn()
    cur = conn.execute(
        "SELECT ticket_no, customer_name, description, status, created_at FROM support_tickets WHERE ticket_no = ?",
        (ticket_no,),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "ticket_no": row[0],
        "customer_name": row[1],
        "description": row[2],
        "status": row[3],
        "created_at": row[4],
    }

def list_tickets(limit: int = 100) -> List[Dict[str, Any]]:
    """List latest tickets."""
    conn = get_conn()
    cur = conn.execute(
        "SELECT ticket_no, customer_name, description, status, created_at FROM support_tickets ORDER BY created_at DESC LIMIT ?",
        (limit,),
    )
    rows = [
        {
            "ticket_no": r[0],
            "customer_name": r[1],
            "description": r[2],
            "status": r[3],
            "created_at": r[4],
        }
        for r in cur.fetchall()
    ]
    conn.close()
    return rows

def log_event(level: str, agent: str, event: str, details: str = "") -> None:
    """Insert a new log entry."""
    conn = get_conn()
    with conn:
        conn.execute(
            "INSERT INTO app_logs (level, agent, event, details) VALUES (?, ?, ?, ?)",
            (level, agent, event, details),
        )
    conn.close()

def list_logs(limit: int = 200) -> List[Dict[str, Any]]:
    """List most recent logs."""
    conn = get_conn()
    cur = conn.execute(
        "SELECT ts, level, agent, event, details FROM app_logs ORDER BY ts DESC LIMIT ?",
        (limit,),
    )
    rows = [
        {"ts": r[0], "level": r[1], "agent": r[2], "event": r[3], "details": r[4]}
        for r in cur.fetchall()
    ]
    conn.close()
    return rows
