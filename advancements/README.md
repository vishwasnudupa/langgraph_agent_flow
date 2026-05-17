# Phase 2: Advancements & Structured ReAct

This directory (`advancements/`) represents Phase 2 of the Kernel Coding Agent. Here, we hardened the "nervous system" of the LangGraph architecture.

## What was built in this phase?

1. **Pydantic Structured Outputs**: We eliminated brittle regex/string parsing for inter-agent communication. 
   - We updated `src/core/state.py` to use strict Pydantic objects (like `TestReport` and `ReviewResult`).
   - We updated agents like the Reviewer and Debugger to use LangChain's `.with_structured_output()`, ensuring the LLM always returns a perfectly formatted JSON schema that the graph routing functions can blindly trust.

2. **ReAct Subgraphs**: We upgraded the Builder and Tester agents from plain text generators into fully capable ReAct agents (`create_react_agent`).
   - **The Builder** now writes a patch, invokes the `apply_patch` tool, and if it fails, it can see the error and retry internally *before* it yields back to the main graph.
   - **The Tester** now invokes `run_checkpatch`, `run_sparse`, etc., actively interacting with the mock environment to gather evidence.

## Limitations of Phase 2 (Why we moved to Phase 3)
* **ReAct Infinite Loops**: Because the Builder and Tester are now ReAct agents, they are susceptible to getting stuck in internal loops (e.g., repeatedly trying to compile code with a fatal syntax error). Standard LangGraph ReAct agents loop up to 25 times before crashing, wasting massive amounts of tokens.
* **Overseer Dead Ends**: The Overseer circuit breaker is great at stopping loops, but it immediately halts the graph. A truly autonomous agent should attempt to completely change its strategy before giving up.

To see how we added loop-resistance and automation paradigms, navigate to the [`../phase3/`](../phase3/) directory.
