"""
Analyzer Agent — deep-dives into codebase following the planner's investigation plan.
Uses ReAct pattern with codebase + analysis tools.
"""
from __future__ import annotations

from langgraph.prebuilt import create_react_agent

from src.core.llm import get_llm
from src.core.state import AgentState, InvestigationPlan
from src.tools.codebase_tools import search_code, read_file, list_directory, git_log, git_blame, semantic_search
from src.tools.analysis_tools import parse_c_ast, find_callers, find_definitions, analyze_kconfig

SYSTEM_PROMPT = """You are a kernel codebase analyst investigating a bug.

You have been given an investigation plan. Follow it step by step using your tools:
- search_code: grep for patterns in the source tree
- semantic_search: find code by natural language meaning (RAG)
- read_file: read specific files with line ranges
- list_directory: explore directory structure
- git_log / git_blame: check commit history
- parse_c_ast: extract functions/structs from C files using AST
- find_callers / find_definitions: trace code paths
- analyze_kconfig: check Kconfig dependencies

After investigating, produce a ROOT CAUSE ANALYSIS with:
1. **Root Cause**: One-paragraph explanation of what's wrong
2. **Affected Files**: List of files that need changes
3. **Evidence**: Key code snippets that prove the issue
4. **Fix Strategy**: How to fix it (high-level, not the actual patch)

Be precise — reference exact function names, line numbers, and file paths."""

ANALYZER_TOOLS = [
    semantic_search, search_code, read_file, list_directory, git_log, git_blame,
    parse_c_ast, find_callers, find_definitions, analyze_kconfig,
]


def create_analyzer_agent():
    """Create the analyzer ReAct agent (compiled subgraph)."""
    return create_react_agent(
        model=get_llm(),
        tools=ANALYZER_TOOLS,
        name="analyzer",
        prompt=SYSTEM_PROMPT,
    )


def analyzer_node(state: AgentState) -> dict:
    """Analyzer agent node — investigates codebase and identifies root cause."""
    agent = create_analyzer_agent()

    # Format the Pydantic plan object into a string for the prompt
    plan_obj = state.get('plan')
    plan_text = "No plan provided"
    if plan_obj and isinstance(plan_obj, InvestigationPlan):
        plan_text = "\n".join(f"{i+1}. {step}" for i, step in enumerate(plan_obj.steps))

    prompt = (
        f"Investigation Plan:\n{plan_text}\n\n"
        f"Source tree: {state.get('repo_path', 'Not set')}\n"
        f"Architecture: {state.get('target_arch', 'arm64')}\n"
        f"Component: {state.get('jira_component', 'unknown')}\n"
        f"\nOriginal ticket: {state.get('jira_summary', '')}\n"
        f"{state.get('jira_description', '')}\n\n"
        f"Follow the investigation plan. Use your tools to explore the codebase. "
        f"Then provide your root cause analysis."
    )

    result = agent.invoke(
        {"messages": [{"role": "user", "content": prompt}]},
        config={"recursion_limit": 5}
    )
    final_msg = result["messages"][-1].content

    return {
        "root_cause": final_msg,
        "current_phase": "analyzer",
        "phase_history": ["analyzer"],
    }
