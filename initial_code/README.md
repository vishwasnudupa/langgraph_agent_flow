# Phase 1: The Baseline Prototype

This directory (`initial_code/`) contains the foundational Phase 1 implementation of the Kernel Coding Agent. 

## What was built in this phase?

1. **StateGraph Orchestration**: We mapped out the engineering workflow into a LangGraph `StateGraph` in `src/graph/orchestrator.py`. This defined the core routing between the Planner, Analyzer, Builder, Reviewer, Tester, and Debugger.
2. **Circuit Breaking (Overseer)**: We introduced the `overseer.py` node. Early autonomous agents often get stuck in infinite failure loops (e.g., Builder writes bad code -> Reviewer rejects -> Builder writes same bad code). The Overseer hashes the graph state to detect these loops and halts the pipeline to save API tokens.
3. **Evolution Memory**: We created `src/memory/evolution_store.py` (backed by SQLite) to allow the agent to remember how it fixed previous bugs in specific subsystems, mirroring how senior engineers rely on past experience.

## Limitations of Phase 1 (Why we moved to Phase 2)
While structurally sound, this baseline suffers from a few critical flaws:
* **Brittle Parsing**: Agents output verdicts as raw strings (e.g., `"VERDICT: APPROVE"`). The graph routes based on `if "APPROVE" in string`, which easily breaks if the LLM gets conversational.
* **Fake Tooling**: The Builder and Tester agents are just text generators. They don't actually invoke the mock build or test tools; they just pretend they did.

To see how these were fixed, navigate to the [`../advancements/`](../advancements/) directory.
