"""
Overseer — circuit breaker that prevents infinite loops and runaway token usage.
Upgraded in Phase 3 to support Paradigm Shifts before halting.
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
    # Read from structured outputs if they exist
    review_verdict = ""
    if "review" in state and hasattr(state["review"], "verdict"):
        review_verdict = state["review"].verdict
        
    test_status = ""
    if "test_report" in state and hasattr(state["test_report"], "overall_status"):
        test_status = state["test_report"].overall_status
        
    debug_str = ""
    if "debug_analysis" in state and hasattr(state["debug_analysis"], "root_cause_analysis"):
        debug_str = state["debug_analysis"].root_cause_analysis[:200]

    key_fields = {
        "patch": state.get("patch", ""),
        "build_status": state.get("build_status", ""),
        "review_verdict": review_verdict,
        "test_status": test_status,
        "debug_analysis": debug_str,
    }
    raw = json.dumps(key_fields, sort_keys=True)
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def overseer_node(state: AgentState) -> dict:
    """
    Overseer node — circuit breaker before retry.

    Checks:
    1. Retry count vs max
    2. State hash deduplication (are we looping with identical state?)
    
    If it trips, triggers a Paradigm Shift (is_paradigm_shift = True).
    If it trips AGAIN after a Paradigm Shift, sets error to halt the graph.
    """
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)
    is_paradigm_shift = state.get("is_paradigm_shift", False)
    
    trip_reason = None

    # Check retry limit
    if retry_count >= max_retries:
        trip_reason = f"Max retries ({max_retries}) exceeded."

    # Check for identical state loops
    h = _hash_state(state)
    _state_hashes.append(h)
    same_count = _state_hashes.count(h)

    if same_count >= _CIRCUIT_BREAKER_THRESHOLD:
        trip_reason = f"Identical state loop detected ({same_count} times)."

    if trip_reason:
        # If we already tried a paradigm shift and it still tripped, hard fail.
        if is_paradigm_shift:
            return {
                "error": f"Circuit breaker HALT: {trip_reason} (Paradigm Shift failed)",
                "current_phase": "overseer_halt",
                "phase_history": ["overseer:HALT_final"],
            }
        else:
            # Trigger Paradigm Shift
            return {
                "is_paradigm_shift": True,
                "current_phase": "overseer_paradigm_shift",
                "phase_history": [f"overseer:PARADIGM_SHIFT({trip_reason})"],
                # Reset retry count to give the paradigm shift a chance
                "retry_count": 0,
            }

    # All clear — allow retry
    return {
        "error": "", 
        "current_phase": "overseer_pass",
        "phase_history": [f"overseer:PASS(retry={retry_count},hash={h})"],
    }


def reset_overseer():
    """Reset the overseer state (for testing or new pipeline runs)."""
    global _state_hashes
    _state_hashes = []
