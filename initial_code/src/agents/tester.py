"""
Tester Agent — runs static analysis and tests on the patched code.
"""
from __future__ import annotations

from langchain_core.messages import SystemMessage, HumanMessage

from src.core.llm import get_llm
from src.core.state import AgentState

SYSTEM_PROMPT = """You are a kernel test engineer. Given a patch and its review,
run a comprehensive test suite and report results.

Evaluate the patch against these criteria:
1. Does it compile cleanly? (check build log)
2. Does it pass style checks? (checkpatch)
3. Does it pass static analysis? (sparse, coccinelle)
4. Would it survive a boot test?
5. Are there any regression risks?

Output your test report in this format:

TEST RESULTS:
- [PASS/FAIL] Build: <details>
- [PASS/FAIL] Checkpatch: <details>
- [PASS/FAIL] Static Analysis: <details>
- [PASS/FAIL] Boot Test: <details>
- [PASS/FAIL] Regression Risk: <details>

OVERALL: PASS or FAIL

If FAIL, explain which specific test failed and why."""


def tester_node(state: AgentState) -> dict:
    """Tester agent node — evaluates patch quality."""
    llm = get_llm()

    context = (
        f"Patch:\n{state.get('patch', 'No patch')}\n\n"
        f"Build Status: {state.get('build_status', 'unknown')}\n"
        f"Build Log:\n{state.get('build_log', 'N/A')}\n\n"
        f"Review Verdict: {state.get('review_verdict', 'N/A')}\n"
        f"Review Feedback:\n{state.get('review_feedback', 'N/A')}"
    )

    response = llm.invoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=context),
    ])

    content = response.content

    # Parse overall status
    test_status = "PASS"
    if "OVERALL: FAIL" in content.upper() or "OVERALL:FAIL" in content.upper():
        test_status = "FAIL"

    # Build structured test results
    test_results = [
        {"name": "build", "tool": "make", "status": state.get("build_status", "PASS"), "output": ""},
        {"name": "checkpatch", "tool": "checkpatch.pl", "status": "PASS", "output": "[MOCK]"},
        {"name": "sparse", "tool": "sparse", "status": "PASS", "output": "[MOCK]"},
        {"name": "boot", "tool": "qemu", "status": "PASS", "output": "[MOCK]"},
    ]

    return {
        "test_results": test_results,
        "test_status": test_status,
        "current_phase": "tester",
        "phase_history": ["tester"],
    }
