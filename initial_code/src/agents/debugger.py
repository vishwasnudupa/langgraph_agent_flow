"""
Debugger Agent — activated on failure. Analyzes what went wrong and proposes a fix strategy.
"""
from __future__ import annotations

from langchain_core.messages import SystemMessage, HumanMessage

from src.core.llm import get_llm
from src.core.state import AgentState

SYSTEM_PROMPT = """You are a kernel debugging expert. A patch attempt has FAILED
(either build failure, test failure, or review rejection).

Your job is to:
1. Analyze the failure evidence (build logs, test results, review feedback)
2. Identify the SPECIFIC technical reason it failed
3. Propose a CONCRETE fix strategy for the Builder agent to retry

Output in this format:

FAILURE ANALYSIS:
What failed: <build/test/review>
Root technical cause: <specific reason — not vague>
Evidence: <quote the relevant error or feedback>

PROPOSED FIX:
<Specific, actionable instructions for the Builder agent.
Reference exact function names, line numbers, and what to change.
Do NOT write the patch yourself — instruct the Builder.>

CONFIDENCE: <HIGH/MEDIUM/LOW>

Be precise. The Builder will use your analysis verbatim to retry."""


def debugger_node(state: AgentState) -> dict:
    """Debugger agent node — analyzes failure and proposes fix."""
    llm = get_llm()

    # Collect all failure evidence
    evidence_parts = [
        f"Retry attempt: {state.get('retry_count', 0) + 1}",
        f"\nPrevious patch:\n{state.get('patch', 'N/A')}",
    ]

    if state.get("build_status") == "FAIL":
        evidence_parts.append(f"\nBuild Log (FAILED):\n{state.get('build_log', 'N/A')}")

    if state.get("review_verdict") == "REQUEST_CHANGES":
        evidence_parts.append(f"\nReview Feedback (CHANGES REQUESTED):\n{state.get('review_feedback', 'N/A')}")

    if state.get("test_status") == "FAIL":
        test_details = "\n".join(
            f"  {t.get('name', '?')}: {t.get('status', '?')} — {t.get('output', '')}"
            for t in state.get("test_results", [])
        )
        evidence_parts.append(f"\nTest Results (FAILED):\n{test_details}")

    evidence = "\n".join(evidence_parts)

    response = llm.invoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=evidence),
    ])

    content = response.content
    retry_count = state.get("retry_count", 0) + 1

    return {
        "debug_analysis": content,
        "proposed_fix": content,  # Builder reads this on retry
        "retry_count": retry_count,
        "current_phase": "debugger",
        "phase_history": ["debugger"],
    }
