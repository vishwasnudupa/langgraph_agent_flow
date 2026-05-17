"""
Routing — conditional edge functions for the LangGraph pipeline.
Upgraded to check Pydantic structured output fields.
"""
from __future__ import annotations

from src.core.state import AgentState


def route_after_review(state: AgentState) -> str:
    """Route after the Reviewer agent."""
    if "review" in state and state["review"].verdict == "REQUEST_CHANGES":
        return "debugger"
    return "tester"


def route_after_test(state: AgentState) -> str:
    """Route after the Tester agent."""
    if "test_report" in state and state["test_report"].overall_status == "FAIL":
        return "debugger"
    return "finalize"


def route_after_debug(state: AgentState) -> str:
    """Route after the Debugger agent."""
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)

    if retry_count >= max_retries:
        return "escalate"
    return "overseer"


def route_overseer(state: AgentState) -> str:
    """Route after the Overseer's circuit-breaker check."""
    if state.get("error"):
        return "circuit_break"
    if state.get("current_phase") == "overseer_paradigm_shift":
        return "paradigm_shift"
    return "builder"
