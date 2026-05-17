"""
AgentState — The central state schema shared by all agents in the graph.

Every node receives this state, reads what it needs, and returns partial updates.
LangGraph merges the updates automatically.
"""
from __future__ import annotations

import operator
from typing import Annotated, Any

from langgraph.graph import add_messages
from typing_extensions import TypedDict


class TestResult(TypedDict, total=False):
    """Single test result entry."""
    name: str
    tool: str        # e.g. "checkpatch", "sparse", "build", "boot"
    status: str      # PASS / FAIL / SKIP
    output: str
    details: str


class AgentState(TypedDict, total=False):
    """
    Master state flowing through the LangGraph pipeline.

    Fields marked with Annotated[..., operator.add] are append-only lists —
    LangGraph will concatenate updates instead of overwriting.
    """

    # ── Jira Context ──────────────────────────────────────────────────
    jira_ticket_id: str
    jira_summary: str
    jira_description: str
    jira_labels: list[str]
    jira_component: str          # e.g. "drivers/i2c"
    jira_priority: str           # e.g. "High", "Critical"

    # ── Codebase Context ──────────────────────────────────────────────
    repo_path: str               # local path to source tree
    target_arch: str             # arm64, x86_64, riscv
    relevant_files: list[str]    # files identified by analyzer
    code_snippets: dict[str, str]  # filename → content excerpt
    symbol_table: dict[str, Any]   # tree-sitter extracted symbols

    # ── Agent Outputs ─────────────────────────────────────────────────
    plan: str                    # planner's investigation plan
    root_cause: str              # analyzer's root-cause hypothesis
    patch: str                   # unified diff
    patch_files: dict[str, str]  # filename → patched content
    build_log: str
    build_status: str            # PASS / FAIL
    review_feedback: str
    review_verdict: str          # APPROVE / REQUEST_CHANGES
    test_results: list[TestResult]
    test_status: str             # PASS / FAIL
    debug_analysis: str          # debugger's failure analysis
    proposed_fix: str            # debugger's fix suggestion

    # ── Control Flow ──────────────────────────────────────────────────
    messages: Annotated[list, add_messages]
    current_phase: str
    retry_count: int
    max_retries: int             # default 3
    error: str
    phase_history: Annotated[list[str], operator.add]  # audit trail

    # ── Evolution Memory ──────────────────────────────────────────────
    evolution_context: list[dict[str, Any]]  # past similar fixes
