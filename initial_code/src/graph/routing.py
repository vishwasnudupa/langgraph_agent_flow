"""
Routing — conditional edge functions for the LangGraph pipeline.
"""
from __future__ import annotations

from src.core.state import AgentState


def route_after_review(state: AgentState) -> str:
    """Route after the Reviewer agent.

    Returns:
        "tester" if approved, "debugger" if changes requested.
    """
    verdict = state.get("review_verdict", "APPROVE")
    if verdict == "REQUEST_CHANGES":
        return "debugger"
    return "tester"


def route_after_test(state: AgentState) -> str:
    """Route after the Tester agent.

    Returns:
        "finalize" if all tests pass, "debugger" if any fail.
    """
    status = state.get("test_status", "PASS")
    if status == "FAIL":
        return "debugger"
    return "finalize"


def route_after_debug(state: AgentState) -> str:
    """Route after the Debugger agent.

    Returns:
        "overseer" to check circuit breaker before retry,
        or "escalate" if max retries exceeded.
    """
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)

    if retry_count >= max_retries:
        return "escalate"
    return "overseer"


def route_overseer(state: AgentState) -> str:
    """Route after the Overseer's circuit-breaker check.

    Returns:
        "builder" to retry, or "circuit_break" to halt.
    """
    # The overseer node sets error if circuit breaker trips
    if state.get("error"):
        return "circuit_break"
    return "builder"
