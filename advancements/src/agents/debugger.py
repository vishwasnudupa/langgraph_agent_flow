"""
Debugger Agent — activated on failure. Analyzes what went wrong and proposes a fix strategy.
Upgraded to use structured outputs.
"""
from __future__ import annotations

from langchain_core.messages import SystemMessage, HumanMessage

from src.core.llm import get_llm
from src.core.state import AgentState, DebugAnalysis

SYSTEM_PROMPT = """You are a kernel debugging expert. A patch attempt has FAILED
(either build failure, test failure, or review rejection).

Your job is to:
1. Analyze the failure evidence (build logs, test results, review feedback)
2. Identify the SPECIFIC technical reason it failed
3. Propose a CONCRETE fix strategy for the Builder agent to retry

Be precise. The Builder will use your analysis verbatim to retry."""


def debugger_node(state: AgentState) -> dict:
    """Debugger agent node — analyzes failure and proposes fix."""
    llm = get_llm().with_structured_output(DebugAnalysis)

    # Collect all failure evidence
    evidence_parts = [
        f"Retry attempt: {state.get('retry_count', 0) + 1}",
        f"\nPrevious patch:\n{state.get('patch', 'N/A')}",
    ]

    if state.get("build_status") == "FAIL":
        evidence_parts.append(f"\nBuild Log (FAILED):\n{state.get('build_log', 'N/A')}")

    if "review" in state and state["review"].verdict == "REQUEST_CHANGES":
        evidence_parts.append(f"\nReview Feedback (CHANGES REQUESTED):\n{state['review'].feedback}")

    if "test_report" in state and state["test_report"].overall_status == "FAIL":
        test_details = "\n".join(
            f"  {t.name}: {t.status} — {t.output}"
            for t in state["test_report"].test_details
        )
        evidence_parts.append(f"\nTest Results (FAILED):\n{test_details}")

    evidence = "\n".join(evidence_parts)

    response: DebugAnalysis = llm.invoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=evidence),
    ])

    retry_count = state.get("retry_count", 0) + 1

    return {
        "debug_analysis": response,
        "retry_count": retry_count,
        "current_phase": "debugger",
        "phase_history": ["debugger"],
    }
