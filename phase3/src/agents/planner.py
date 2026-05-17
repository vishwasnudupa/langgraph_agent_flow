"""
Planner Agent — reads Jira ticket and produces an investigation plan.
Upgraded to use structured outputs.
"""
from __future__ import annotations

from langchain_core.messages import SystemMessage, HumanMessage

from src.core.llm import get_llm
from src.core.state import AgentState, InvestigationPlan

SYSTEM_PROMPT = """You are a senior kernel/firmware engineer triaging a bug report.

Given a Jira ticket, produce a concise investigation plan with numbered steps.
Each step should specify:
1. What subsystem/file to look at and why
2. What to search for (function names, error strings, config symbols)
3. What hypothesis to test

Keep the plan to 5-8 steps maximum. Be specific — reference real kernel subsystems
(drivers/i2c, kernel/sched, mm/, etc.) based on the ticket's component and labels.

If evolution context (past fixes) is provided, incorporate those lessons."""


def planner_node(state: AgentState) -> dict:
    """Planner agent node — creates investigation plan from Jira ticket."""
    llm = get_llm().with_structured_output(InvestigationPlan)

    # Build context from ticket
    ticket_context = (
        f"Ticket: {state.get('jira_ticket_id', 'N/A')}\n"
        f"Summary: {state.get('jira_summary', 'N/A')}\n"
        f"Component: {state.get('jira_component', 'N/A')}\n"
        f"Priority: {state.get('jira_priority', 'Medium')}\n"
        f"Labels: {', '.join(state.get('jira_labels', []))}\n"
        f"\nDescription:\n{state.get('jira_description', 'No description')}"
    )

    # Add evolution context if available
    evo = state.get("evolution_context", [])
    if evo:
        evo_text = "\n\nPast similar fixes (from evolution memory):\n"
        for e in evo[:3]:
            evo_text += f"  - {e.get('symptom', '')}: {e.get('root_cause', '')}\n"
        ticket_context += evo_text

    response: InvestigationPlan = llm.invoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=ticket_context),
    ])

    return {
        "plan": response,
        "current_phase": "planner",
        "phase_history": ["planner"],
    }
