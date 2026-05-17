"""
Builder Agent — generates a kernel patch and builds it.
Upgraded to a ReAct agent.
"""
from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field

from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.prebuilt import create_react_agent

from src.core.llm import get_llm
from src.core.state import AgentState
from src.tools.build_tools import apply_patch, build_kernel, build_module, check_build_errors

SYSTEM_PROMPT = """You are a kernel patch author. Your job is to generate a patch, 
apply it, and build the source tree to ensure it compiles.

Use your tools iteratively:
1. Write a patch.
2. `apply_patch` to test if it applies.
3. `build_kernel` or `build_module` to compile.
4. `check_build_errors` to parse the build log.

If the build fails, revise your patch and try again.
Once successful (or if you hit a wall), output your final results."""

BUILDER_TOOLS = [apply_patch, build_kernel, build_module, check_build_errors]


class BuilderOutput(BaseModel):
    patch: str = Field(description="The final unified diff patch including commit message")
    build_log: str = Field(description="The final build log output")
    build_status: Literal["PASS", "FAIL"] = Field(description="Final build verdict")


def builder_node(state: AgentState) -> dict:
    """Builder agent node — writes and builds patch."""
    llm = get_llm()
    agent = create_react_agent(
        model=llm,
        tools=BUILDER_TOOLS,
        prompt=SYSTEM_PROMPT,
        response_format=BuilderOutput,
    )

    context = (
        f"Root Cause Analysis:\n{state.get('root_cause', 'No analysis')}\n\n"
        f"Component: {state.get('jira_component', 'unknown')}\n"
        f"Architecture: {state.get('target_arch', 'arm64')}\n"
        f"Source Tree: {state.get('repo_path', 'unknown')}\n"
    )

    # On retry, include debug feedback
    retry = state.get("retry_count", 0)
    if retry > 0 and "debug_analysis" in state:
        dbg = state["debug_analysis"]
        context += (
            f"\n⚠ RETRY #{retry} — Previous attempt failed.\n"
            f"Debug Analysis:\n{dbg.root_cause_analysis}\n"
            f"Proposed Fix Strategy:\n{dbg.proposed_fix_strategy}\n"
            f"\nPrevious patch that failed:\n{state.get('patch', 'N/A')}\n"
            f"\nDo NOT repeat the same mistake. Apply the debug feedback."
        )

    # Include relevant code snippets
    snippets = state.get("code_snippets", {})
    if snippets:
        context += "\n\nRelevant source code:\n"
        for fname, content in list(snippets.items())[:3]:
            context += f"\n── {fname} ──\n{content[:1500]}\n"

    result = agent.invoke({"messages": [{"role": "user", "content": context}]})

    output = result.get("structured_response")
    if not output:
        # Fallback extraction
        extractor = llm.with_structured_output(BuilderOutput)
        output = extractor.invoke(result["messages"])

    return {
        "patch": output.patch,
        "build_log": output.build_log,
        "build_status": output.build_status,
        "current_phase": "builder",
        "phase_history": ["builder"],
    }
