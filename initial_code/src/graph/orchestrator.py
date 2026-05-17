"""
Orchestrator — assembles the full LangGraph StateGraph pipeline.

Pipeline flow:
  jira_ingest → planner → analyzer → builder → reviewer
                                                   ↓
                                    ┌─── tester ←──┘ (if APPROVE)
                                    │       ↓
                                    │   finalize (if PASS) → END
                                    │       ↓
                                    └── debugger (if FAIL)
                                            ↓
                                        overseer → builder (retry)
                                            ↓
                                          END (circuit break / escalate)
"""
from __future__ import annotations

import json
from pathlib import Path

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from src.core.config import get_settings
from src.core.state import AgentState
from src.agents.planner import planner_node
from src.agents.analyzer import analyzer_node
from src.agents.builder import builder_node
from src.agents.reviewer import reviewer_node
from src.agents.tester import tester_node
from src.agents.debugger import debugger_node
from src.graph.overseer import overseer_node, reset_overseer
from src.graph.routing import (
    route_after_review,
    route_after_test,
    route_after_debug,
    route_overseer,
)
from src.tools.jira_tools import load_mock_ticket


# ── Jira Ingest Node ─────────────────────────────────────────────────

def jira_ingest_node(state: AgentState) -> dict:
    """Load ticket data into state (mock or real)."""
    ticket_id = state.get("jira_ticket_id", "")

    # Try to load from mock store (already loaded by CLI)
    from src.tools.jira_tools import _MOCK_TICKETS
    if ticket_id in _MOCK_TICKETS:
        ticket = _MOCK_TICKETS[ticket_id]
    else:
        ticket = {
            "ticket_id": ticket_id,
            "summary": state.get("jira_summary", "Unknown ticket"),
            "description": state.get("jira_description", ""),
            "labels": state.get("jira_labels", []),
            "component": state.get("jira_component", "kernel"),
            "priority": state.get("jira_priority", "Medium"),
        }

    return {
        "jira_ticket_id": ticket.get("ticket_id", ticket_id),
        "jira_summary": ticket.get("summary", ""),
        "jira_description": ticket.get("description", ""),
        "jira_labels": ticket.get("labels", []),
        "jira_component": ticket.get("component", ""),
        "jira_priority": ticket.get("priority", "Medium"),
        "current_phase": "jira_ingest",
        "phase_history": ["jira_ingest"],
        "retry_count": 0,
        "max_retries": get_settings().max_retries,
    }


# ── Finalize Node ────────────────────────────────────────────────────

def finalize_node(state: AgentState) -> dict:
    """Wrap up: log success, update Jira status."""
    from src.tools.jira_tools import _MOCK_TICKETS, _MOCK_COMMENTS

    ticket_id = state.get("jira_ticket_id", "")

    # Update mock Jira
    if ticket_id in _MOCK_TICKETS:
        _MOCK_TICKETS[ticket_id]["status"] = "Done"

    summary = (
        f"✅ Fix completed for {ticket_id}\n"
        f"Root cause: {state.get('root_cause', 'N/A')[:200]}\n"
        f"Retries: {state.get('retry_count', 0)}\n"
        f"Review: {state.get('review_verdict', 'N/A')}\n"
        f"Tests: {state.get('test_status', 'N/A')}"
    )

    _MOCK_COMMENTS.setdefault(ticket_id, []).append(summary)

    return {
        "current_phase": "finalize",
        "phase_history": ["finalize"],
    }


# ── Escalation Node ─────────────────────────────────────────────────

def escalate_node(state: AgentState) -> dict:
    """Human escalation — max retries exceeded."""
    return {
        "current_phase": "escalated",
        "error": (
            f"Max retries ({state.get('max_retries', 3)}) exceeded. "
            f"Last debug analysis:\n{state.get('debug_analysis', 'N/A')[:300]}"
        ),
        "phase_history": ["escalated"],
    }


# ── Graph Assembly ───────────────────────────────────────────────────

def build_graph() -> StateGraph:
    """Assemble and return the compiled LangGraph pipeline."""
    reset_overseer()

    graph = StateGraph(AgentState)

    # ── Add nodes ──
    graph.add_node("jira_ingest", jira_ingest_node)
    graph.add_node("planner", planner_node)
    graph.add_node("analyzer", analyzer_node)
    graph.add_node("builder", builder_node)
    graph.add_node("reviewer", reviewer_node)
    graph.add_node("tester", tester_node)
    graph.add_node("debugger", debugger_node)
    graph.add_node("overseer", overseer_node)
    graph.add_node("finalize", finalize_node)
    graph.add_node("escalate", escalate_node)

    # ── Happy path edges ──
    graph.add_edge(START, "jira_ingest")
    graph.add_edge("jira_ingest", "planner")
    graph.add_edge("planner", "analyzer")
    graph.add_edge("analyzer", "builder")
    graph.add_edge("builder", "reviewer")

    # ── Conditional: after review ──
    graph.add_conditional_edges(
        "reviewer",
        route_after_review,
        {"tester": "tester", "debugger": "debugger"},
    )

    # ── Conditional: after test ──
    graph.add_conditional_edges(
        "tester",
        route_after_test,
        {"finalize": "finalize", "debugger": "debugger"},
    )

    # ── Conditional: after debug ──
    graph.add_conditional_edges(
        "debugger",
        route_after_debug,
        {"overseer": "overseer", "escalate": "escalate"},
    )

    # ── Conditional: overseer circuit breaker ──
    graph.add_conditional_edges(
        "overseer",
        route_overseer,
        {"builder": "builder", "circuit_break": "escalate"},
    )

    # ── Terminal edges ──
    graph.add_edge("finalize", END)
    graph.add_edge("escalate", END)

    return graph


def compile_graph(checkpointer=None):
    """Build and compile the graph with optional checkpointer."""
    graph = build_graph()
    if checkpointer is None:
        checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)
