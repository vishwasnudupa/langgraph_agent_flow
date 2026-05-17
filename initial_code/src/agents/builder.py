"""
Builder Agent — generates a kernel patch based on root-cause analysis.
"""
from __future__ import annotations

from langchain_core.messages import SystemMessage, HumanMessage

from src.core.llm import get_llm
from src.core.state import AgentState

SYSTEM_PROMPT = """You are a kernel patch author. Your job is to generate a correct, minimal
unified diff that fixes the identified root cause.

Rules for your patch:
1. Output a valid unified diff (--- a/file, +++ b/file, @@ hunk headers)
2. Keep changes minimal — fix only what's broken
3. Follow kernel coding style (tabs, 80-col where possible, proper comments)
4. Include appropriate error handling
5. Add a brief commit message at the top in this format:

Subject: [PATCH] subsystem: brief description

Detailed explanation of what was wrong and why this fix is correct.

Signed-off-by: AI Agent <agent@kernel-coding-agent>
---

Then the unified diff.

If this is a RETRY after a failed build/test, incorporate the debug analysis
to fix the specific issue that caused the failure. Do NOT repeat the same mistake.

Output ONLY the commit message + diff. No extra commentary."""


def builder_node(state: AgentState) -> dict:
    """Builder agent node — generates patch from root-cause analysis."""
    llm = get_llm()

    context = (
        f"Root Cause Analysis:\n{state.get('root_cause', 'No analysis')}\n\n"
        f"Component: {state.get('jira_component', 'unknown')}\n"
        f"Architecture: {state.get('target_arch', 'arm64')}\n"
    )

    # On retry, include debug feedback
    retry = state.get("retry_count", 0)
    if retry > 0:
        context += (
            f"\n⚠ RETRY #{retry} — Previous attempt failed.\n"
            f"Debug Analysis:\n{state.get('debug_analysis', 'N/A')}\n"
            f"Proposed Fix Strategy:\n{state.get('proposed_fix', 'N/A')}\n"
            f"\nPrevious patch that failed:\n{state.get('patch', 'N/A')}\n"
            f"\nDo NOT repeat the same mistake. Apply the debug feedback."
        )

    # Include relevant code snippets for context
    snippets = state.get("code_snippets", {})
    if snippets:
        context += "\n\nRelevant source code:\n"
        for fname, content in list(snippets.items())[:3]:
            context += f"\n── {fname} ──\n{content[:1500]}\n"

    response = llm.invoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=context),
    ])

    patch = response.content

    # Simulate build (always passes in Phase 1 mock)
    build_status = "PASS"
    build_log = f"[MOCK] Build of patched source — 0 errors, 0 warnings\nStatus: PASS"

    return {
        "patch": patch,
        "build_log": build_log,
        "build_status": build_status,
        "current_phase": "builder",
        "phase_history": ["builder"],
    }
