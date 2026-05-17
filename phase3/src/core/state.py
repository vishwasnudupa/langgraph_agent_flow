"""
AgentState — The central state schema shared by all agents in the graph.
Upgraded to use Pydantic models for structured agent outputs.
"""
from __future__ import annotations

import operator
from typing import Annotated, Any, Literal

from langgraph.graph import add_messages
from pydantic import BaseModel, Field
from typing_extensions import TypedDict


# ── Pydantic Models for Structured Outputs ──────────────────────────

class TestResult(BaseModel):
    """Single test result entry."""
    name: str = Field(description="Name of the test (e.g., build, sparse, checkpatch)")
    tool: str = Field(description="Tool used")
    status: Literal["PASS", "FAIL", "SKIP"]
    output: str = Field(description="Test output or summary")


class TestReport(BaseModel):
    """Structured report from the Tester agent."""
    overall_status: Literal["PASS", "FAIL"]
    test_details: list[TestResult]


class ReviewResult(BaseModel):
    """Structured verdict from the Reviewer agent."""
    verdict: Literal["APPROVE", "REQUEST_CHANGES"]
    feedback: str


class DebugAnalysis(BaseModel):
    """Structured failure analysis from the Debugger agent."""
    root_cause_analysis: str
    proposed_fix_strategy: str
    confidence: Literal["HIGH", "MEDIUM", "LOW"]


class InvestigationPlan(BaseModel):
    """Structured plan from the Planner agent."""
    steps: list[str]


# ── Master Graph State ──────────────────────────────────────────────

class AgentState(TypedDict, total=False):
    """
    Master state flowing through the LangGraph pipeline.
    """
    # ── Jira Context ──────────────────────────────────────────────────
    jira_ticket_id: str
    jira_summary: str
    jira_description: str
    jira_labels: list[str]
    jira_component: str
    jira_priority: str

    # ── Codebase Context ──────────────────────────────────────────────
    repo_path: str
    target_arch: str
    relevant_files: list[str]
    code_snippets: dict[str, str]
    symbol_table: dict[str, Any]

    # ── Agent Outputs (Structured) ────────────────────────────────────
    plan: InvestigationPlan
    root_cause: str
    patch: str
    patch_files: dict[str, str]
    build_log: str
    build_status: Literal["PASS", "FAIL", "unknown"]
    review: ReviewResult
    test_report: TestReport
    debug_analysis: DebugAnalysis

    # ── Control Flow ──────────────────────────────────────────────────
    messages: Annotated[list, add_messages]
    current_phase: str
    retry_count: int
    max_retries: int
    error: str
    phase_history: Annotated[list[str], operator.add]
    is_paradigm_shift: bool

    # ── Evolution Memory ──────────────────────────────────────────────
    evolution_context: list[dict[str, Any]]
