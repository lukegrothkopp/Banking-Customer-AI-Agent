import sqlite3


def get_ticket(ticket_no: str) -> Optional[Dict[str, Any]]:
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
conn = get_conn()
with conn:
conn.execute(
"INSERT INTO app_logs (level, agent, event, details) VALUES (?, ?, ?, ?)",
(level, agent, event, details),
)
conn.close()




def list_logs(limit: int = 200) -> List[Dict[str, Any]]:
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
