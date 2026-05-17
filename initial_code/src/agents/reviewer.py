"""
Reviewer Agent — code-reviews the generated patch for correctness and style.
"""
from __future__ import annotations

from langchain_core.messages import SystemMessage, HumanMessage

from src.core.llm import get_llm
from src.core.state import AgentState

SYSTEM_PROMPT = """You are a senior kernel code reviewer. Review the given patch for:

1. **Correctness**: Does the fix actually address the root cause? Any logic errors?
2. **Error handling**: Are all error paths handled (NULL checks, return codes)?
3. **Concurrency**: Any race conditions, missing locks, or spinlock issues?
4. **Memory**: Any leaks, use-after-free, or double-free risks?
5. **Style**: Follows kernel coding style? (tabs, naming, comment format)
6. **Commit message**: Clear subject line? Adequate explanation?

Output your review in this format:

VERDICT: APPROVE or REQUEST_CHANGES

FEEDBACK:
- [CRITICAL/WARNING/NIT] description of issue (file:line if applicable)

If APPROVE, you may still list minor nits.
If REQUEST_CHANGES, list the specific problems that must be fixed.

Be strict but fair — this patch goes into a production kernel."""


def reviewer_node(state: AgentState) -> dict:
    """Reviewer agent node — code-reviews the patch."""
    llm = get_llm()

    context = (
        f"Root Cause:\n{state.get('root_cause', 'N/A')}\n\n"
        f"Patch:\n{state.get('patch', 'No patch generated')}\n\n"
        f"Build Status: {state.get('build_status', 'unknown')}\n"
        f"Build Log:\n{state.get('build_log', 'N/A')}"
    )

    response = llm.invoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=context),
    ])

    content = response.content

    # Parse verdict from response
    verdict = "APPROVE"
    if "REQUEST_CHANGES" in content.upper():
        verdict = "REQUEST_CHANGES"

    return {
        "review_feedback": content,
        "review_verdict": verdict,
        "current_phase": "reviewer",
        "phase_history": ["reviewer"],
    }
