"""
Evolution Store — SQLite-backed memory of past fixes.

Agents query this to learn from previous debugging sessions.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from src.core.config import get_settings


def _get_db_path() -> Path:
    """Get the evolution DB path, creating parent dirs if needed."""
    db_path = Path(get_settings().evolution_db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path


def _get_connection() -> sqlite3.Connection:
    """Get a SQLite connection with the schema initialized."""
    conn = sqlite3.connect(str(_get_db_path()))
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS evolutions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id   TEXT NOT NULL,
            subsystem   TEXT,
            symptom     TEXT,
            root_cause  TEXT,
            fix_patch   TEXT,
            retries     INTEGER DEFAULT 0,
            success     BOOLEAN DEFAULT 1,
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    return conn


def record_evolution(
    ticket_id: str,
    subsystem: str,
    symptom: str,
    root_cause: str,
    fix_patch: str,
    retries: int = 0,
    success: bool = True,
) -> int:
    """Record a completed fix in the evolution store. Returns the row ID."""
    conn = _get_connection()
    cursor = conn.execute(
        """INSERT INTO evolutions (ticket_id, subsystem, symptom, root_cause, fix_patch, retries, success)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (ticket_id, subsystem, symptom, root_cause, fix_patch, retries, success),
    )
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id


def query_similar(subsystem: str = "", symptom: str = "", limit: int = 3) -> list[dict]:
    """
    Query the evolution store for similar past fixes.

    Searches by subsystem and/or symptom keywords.
    Returns list of dicts with keys: ticket_id, subsystem, symptom, root_cause, fix_patch.
    """
    conn = _get_connection()

    conditions = ["success = 1"]
    params = []

    if subsystem:
        conditions.append("subsystem LIKE ?")
        params.append(f"%{subsystem}%")
    if symptom:
        conditions.append("(symptom LIKE ? OR root_cause LIKE ?)")
        params.extend([f"%{symptom}%", f"%{symptom}%"])

    where = " AND ".join(conditions)
    rows = conn.execute(
        f"SELECT * FROM evolutions WHERE {where} ORDER BY created_at DESC LIMIT ?",
        params + [limit],
    ).fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_history(limit: int = 20) -> list[dict]:
    """Get recent evolution history."""
    conn = _get_connection()
    rows = conn.execute(
        "SELECT * FROM evolutions ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]
