"""
Overseer — circuit breaker that prevents infinite loops and runaway token usage.
"""
from __future__ import annotations

import hashlib
import json

from src.core.state import AgentState

# Track state hashes to detect loops
_state_hashes: list[str] = []
_CIRCUIT_BREAKER_THRESHOLD = 3  # same state seen N times = loop


def _hash_state(state: AgentState) -> str:
    """Hash the key parts of state to detect repeated identical states."""
    key_fields = {
        "patch": state.get("patch", ""),
        "build_status": state.get("build_status", ""),
        "review_verdict": state.get("review_verdict", ""),
        "test_status": state.get("test_status", ""),
        "debug_analysis": state.get("debug_analysis", "")[:200],
    }
    raw = json.dumps(key_fields, sort_keys=True)
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def overseer_node(state: AgentState) -> dict:
    """
    Overseer node — circuit breaker before retry.

    Checks:
    1. Retry count vs max
    2. State hash deduplication (are we looping with identical state?)
    3. Logs the transition for audit

    Sets state["error"] if circuit breaker trips, which routing picks up.
    """
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)

    # Check retry limit
    if retry_count >= max_retries:
        return {
            "error": f"Circuit breaker: max retries ({max_retries}) exceeded",
            "current_phase": "overseer_halt",
            "phase_history": ["overseer:HALT_max_retries"],
        }

    # Check for identical state loops
    h = _hash_state(state)
    _state_hashes.append(h)
    same_count = _state_hashes.count(h)

    if same_count >= _CIRCUIT_BREAKER_THRESHOLD:
        return {
            "error": f"Circuit breaker: identical state detected {same_count} times (loop)",
            "current_phase": "overseer_halt",
            "phase_history": [f"overseer:HALT_loop({h})"],
        }

    # All clear — allow retry
    return {
        "error": "",  # clear any previous error
        "current_phase": "overseer_pass",
        "phase_history": [f"overseer:PASS(retry={retry_count},hash={h})"],
    }


def reset_overseer():
    """Reset the overseer state (for testing or new pipeline runs)."""
    global _state_hashes
    _state_hashes = []
