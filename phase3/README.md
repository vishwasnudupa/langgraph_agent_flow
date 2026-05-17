# Phase 3: Automation & Loop Resistance

This directory (`phase3/`) represents the bleeding-edge implementation of the Kernel Coding Agent. It resolves the drawbacks of Phase 2, resulting in a highly autonomous and token-efficient pipeline.

## What was built in this phase?

### 1. Internal Loop Clamping
We introduced a strict `recursion_limit` parameter across all ReAct subgraphs (`analyzer.py`, `builder.py`, `tester.py`). 
* **The Impact**: Instead of an LLM getting confused and looping 25 times over a syntax error (burning tokens and hitting timeouts), it is forced to yield back to the main graph after 5 attempts. If it fails, the failure is cleanly handed off to the Debugger agent for analysis.

### 2. Paradigm Shift Automation (The "Hail Mary")
We vastly improved the autonomy of the `overseer.py` node.
* **The Problem**: In Phase 2, if the agent got stuck proposing the same bad patch 3 times, the Overseer would just give up and stop the graph.
* **The Solution**: The Overseer now sets an `is_paradigm_shift` flag and routes the pipeline *back* to the Debugger. The Debugger is injected with a severe system prompt: *"You are stuck in a loop. COMPLETELY DISCARD your previous strategy. Try a radically different fix."* The Builder then wipes its memory of the old patches and starts fresh based on this radical new approach. 
* **The Impact**: The agent can autonomously dig itself out of local minimums without requiring human intervention.

### 3. Advanced Tooling Infrastructure (RAG & AST)
We refactored `src/tools/analysis_tools.py` and `codebase_tools.py` to prepare for a real Linux kernel environment.
* **AST Parsing Stub**: We removed the brittle Regex parsing for C code and added `parse_c_ast`, a stub designed to interface directly with `tree-sitter-c` for perfect struct/macro extraction.
* **Semantic Search Stub**: We added a `semantic_search` tool designed for RAG (Retrieval-Augmented Generation), allowing the Analyzer to query codebase vectors rather than relying on noisy `grep` operations.

## Running Phase 3
You can run this phase directly using the included CLI:
```bash
# Ensure you have installed dependencies from the root directory
kca run --mock profiles/sample_tickets/kern_i2c_null_deref.json
```
