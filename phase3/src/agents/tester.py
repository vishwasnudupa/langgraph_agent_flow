"""
Tester Agent — runs static analysis and tests on the patched code.
Upgraded to a ReAct agent with structured outputs.
"""
from __future__ import annotations

from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.prebuilt import create_react_agent

from src.core.llm import get_llm
from src.core.state import AgentState, TestReport
from src.tools.test_tools import run_checkpatch, run_sparse, run_coccinelle, run_boot_test

SYSTEM_PROMPT = """You are a kernel test engineer. Given a patch and its review,
run a comprehensive test suite using your tools and report results.

You MUST use your tools to evaluate the patch:
- run_checkpatch: check style
- run_sparse: static analysis
- run_coccinelle: semantic patches
- run_boot_test: boot simulation

After running the tools, you MUST return a final structured report."""

TESTER_TOOLS = [run_checkpatch, run_sparse, run_coccinelle, run_boot_test]


def tester_node(state: AgentState) -> dict:
    """Tester agent node — evaluates patch quality via tool execution."""
    llm = get_llm()

    # The agent uses tools, then its final step must return the structured TestReport
    agent = create_react_agent(
        model=llm,
        tools=TESTER_TOOLS,
        prompt=SYSTEM_PROMPT,
        response_format=TestReport,
    )

    context = (
        f"Source Tree: {state.get('repo_path', 'N/A')}\n"
        f"Patch:\n{state.get('patch', 'No patch')}\n\n"
        f"Build Status: {state.get('build_status', 'unknown')}\n"
    )

    if "review" in state:
        context += f"\nReview Verdict: {state['review'].verdict}\nReview Feedback:\n{state['review'].feedback}"

    result = agent.invoke({"messages": [{"role": "user", "content": context}]})

    # The final message content is the parsed Pydantic object when response_format is used
    # Wait, in create_react_agent, if response_format is passed, the final output is in the last message's parsed/tool_calls or directly returned.
    # Actually, as of langgraph 0.2+, response_format is a valid param and returns a dict with 'structured_response' if configured, OR the final message has it.
    # To be safe and standard with langgraph prebuilt agents:
    # If the LLM just returns text, we might need a dedicated output node, or we can just use the final message.
    # Let's extract the TestReport from the structured output (LangChain parses it).
    
    # In recent LangGraph, `create_react_agent` with `response_format` puts the result in `result["structured_response"]`.
    # Fallback to direct parsing if that key isn't present.
    report = result.get("structured_response")
    
    if not report:
        # Fallback: prompt the LLM one last time to extract the structure from the conversation
        extractor = llm.with_structured_output(TestReport)
        report = extractor.invoke(result["messages"])

    return {
        "test_report": report,
        "current_phase": "tester",
        "phase_history": ["tester"],
    }
