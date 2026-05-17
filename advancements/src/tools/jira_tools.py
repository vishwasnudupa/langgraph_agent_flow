"""
Jira Tools — Mock implementation for Phase 1.

In future phases, swap the mock backend for the real `jira` library.
The tool signatures stay identical so agents don't need to change.
"""
from __future__ import annotations

import json
from pathlib import Path

from langchain_core.tools import tool

# ── In-memory mock store ──────────────────────────────────────────────
_MOCK_TICKETS: dict[str, dict] = {}
_MOCK_COMMENTS: dict[str, list[str]] = {}


def load_mock_ticket(path: str | Path) -> dict:
    """Load a sample ticket JSON into the mock store and return it."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    tid = data["ticket_id"]
    _MOCK_TICKETS[tid] = data
    _MOCK_COMMENTS.setdefault(tid, [])
    return data


# ── Tool definitions (used by agents) ────────────────────────────────

@tool
def fetch_jira_ticket(ticket_id: str) -> dict:
    """
    Fetch a Jira ticket by its ID.

    Returns a dict with keys: ticket_id, summary, description,
    labels, component, priority, status.
    """
    if ticket_id in _MOCK_TICKETS:
        return _MOCK_TICKETS[ticket_id]
    return {
        "ticket_id": ticket_id,
        "summary": f"[MOCK] Ticket {ticket_id} not found in mock store",
        "description": "No mock data loaded. Use load_mock_ticket() first.",
        "labels": [],
        "component": "unknown",
        "priority": "Medium",
        "status": "To Do",
    }


@tool
def update_jira_status(ticket_id: str, status: str) -> str:
    """
    Transition a Jira ticket to a new status.

    Valid statuses: 'To Do', 'In Progress', 'In Review', 'Done'.
    Returns confirmation string.
    """
    if ticket_id in _MOCK_TICKETS:
        old = _MOCK_TICKETS[ticket_id].get("status", "To Do")
        _MOCK_TICKETS[ticket_id]["status"] = status
        return f"[MOCK] {ticket_id}: {old} → {status}"
    return f"[MOCK] {ticket_id} not found, but status noted as {status}"


@tool
def post_jira_comment(ticket_id: str, comment: str) -> str:
    """
    Post a comment on a Jira ticket.

    Used by agents to record progress, findings, and results.
    Returns confirmation string.
    """
    _MOCK_COMMENTS.setdefault(ticket_id, []).append(comment)
    n = len(_MOCK_COMMENTS[ticket_id])
    return f"[MOCK] Comment #{n} posted on {ticket_id}"
