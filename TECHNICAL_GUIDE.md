# 📘 Kernel Coding Agent — Comprehensive Technical Guide

This document serves as the **Definitive Developer and Architecture Guide** for the LangGraph-based Kernel Coding Agent. It details every technical library, module, agent behavior, and control flow mechanism used across the entire project lifecycle (from Phase 1 prototype to Phase 3 Loop-Resistant Automation).

---

## 1. Core Technology Stack

The project relies on a carefully selected stack of modern AI engineering libraries.

### 1.1. Orchestration & LLM Interfacing
*   **LangGraph (`langgraph`)**: The backbone of the project. LangGraph is used to define a cyclic `StateGraph`. Unlike standard linear chains (LangChain), LangGraph allows us to build state machines with conditional routing (e.g., looping back to the Builder if tests fail, or triggering an Overseer circuit breaker).
*   **LangChain Core (`langchain-core`)**: Provides the abstraction layer for LLMs (`SystemMessage`, `HumanMessage`), allowing the agent to switch seamlessly between OpenAI, Anthropic, or Google Gemini models depending on the configuration in `.env`.
*   **ReAct Agents (`langgraph.prebuilt.create_react_agent`)**: Used to encapsulate specific nodes (like the Builder and Tester) into autonomous subgraphs. This allows a node to execute a loop of "Thought -> Action (Tool Call) -> Observation" multiple times before returning to the main graph.

### 1.2. Data Validation & State
*   **Pydantic (`pydantic`)**: Used extensively in Phase 2/3 for **Structured Outputs**. Instead of parsing raw strings (which is highly brittle), we use LangChain's `.with_structured_output()` mapped to Pydantic `BaseModel` classes. This guarantees the LLM returns exactly the JSON schema we need (e.g., `ReviewResult`, `TestReport`), ensuring the graph routing functions never crash due to unexpected text.
*   **Typing (`typing_extensions.TypedDict`)**: Defines the global `AgentState` that flows through every node in the graph, holding the Jira ticket context, codebase snippets, and accumulated agent outputs.

### 1.3. Tooling & Memory
*   **aiosqlite / SQLite3**: Used in `src/memory/evolution_store.py` to persist long-term memory. It acts as an "Evolution Store," recording successful patches so the Planner can retrieve past fixes for similar symptoms in the future.
*   **Tree-sitter (`tree-sitter-c`)**: (Stubbed in Phase 3) Replaces brittle Regex parsing. It generates an Abstract Syntax Tree (AST) of C code, allowing the agent to perfectly extract structs, macros, and function boundaries regardless of complex C preprocessor formatting.
*   **FAISS / sentence-transformers**: (Stubbed in Phase 3) Enables the `semantic_search` tool, allowing the Analyzer to query the massive Linux kernel codebase using natural language vector embeddings (RAG) instead of noisy `grep` operations.

### 1.4. User Interface
*   **Typer & Rich (`typer`, `rich`)**: Powers the `kca` Command Line Interface, providing beautiful, panel-based terminal outputs, progress tracking, and tabular history views.

---

## 2. Global State Schema (`AgentState`)

Everything in LangGraph revolves around the state object. The `AgentState` (defined in `src/core/state.py`) acts as the shared whiteboard for all agents.

**Key Components of the State:**
*   **Jira Context**: `jira_ticket_id`, `jira_summary`, `jira_component`. (Input context).
*   **Graph Modifiers**: `messages` (a LangGraph `add_messages` annotated list storing the dialogue), `current_phase`, and `phase_history`.
*   **Structured Outputs**: `plan` (`InvestigationPlan`), `review` (`ReviewResult`), `test_report` (`TestReport`). These are explicitly typed Pydantic models populated by their respective agents.
*   **Loop Control**: `retry_count`, `max_retries`, `is_paradigm_shift`. These flags dictate how the Overseer routes the graph upon failure.

---

## 3. The 7 Core Nodes (Agents & Overseer)

The system is composed of 6 specialized AI agents and 1 programmatic Supervisor (The Overseer).

### 3.1. The Planner (`planner.py`)
*   **Role**: The architect. It ingests the Jira ticket and queries the Evolution Store for past fixes.
*   **Output**: Returns an `InvestigationPlan` (Pydantic model) containing a strict array of 5-8 numbered steps detailing exactly which kernel subsystems, files, and functions the Analyzer should investigate.

### 3.2. The Analyzer (`analyzer.py`)
*   **Role**: The investigator. It is a ReAct agent equipped with codebase tools.
*   **Flow**: It reads the Planner's steps, executes tools (like `read_file`, `parse_c_ast`, `semantic_search`), and builds context.
*   **Safety Limits**: Configured with `recursion_limit=5` to prevent it from endlessly grepping a massive repository if it gets confused.
*   **Output**: A raw string `root_cause` analysis pinpointing the exact lines of code responsible for the bug.

### 3.3. The Builder (`builder.py`)
*   **Role**: The coder. It is a ReAct agent equipped with `apply_patch` and `build_kernel` tools.
*   **Flow**: It writes a patch and attempts to apply and compile it. If the mock compilation fails (e.g., syntax error), the Builder catches it and retries internally *without* bothering the main graph. 
*   **Paradigm Awareness**: If the graph is in a `paradigm_shift` state, the Builder's prompt forces it to discard all previous patches and write code from scratch.
*   **Output**: A `BuilderOutput` Pydantic model containing the final `patch`, `build_log`, and `build_status`.

### 3.4. The Reviewer (`reviewer.py`)
*   **Role**: The gatekeeper. It evaluates the patch against strict kernel coding guidelines (concurrency, memory leaks, styles).
*   **Flow**: It relies entirely on LLM reasoning (no external tools). It is instructed to be extremely strict.
*   **Output**: A `ReviewResult` Pydantic model containing a strict `APPROVE` or `REQUEST_CHANGES` verdict, and a markdown list of feedback.

### 3.5. The Tester (`tester.py`)
*   **Role**: The QA engineer. It is a ReAct agent equipped with static analysis and boot tools.
*   **Flow**: Invokes `run_checkpatch`, `run_sparse`, `run_coccinelle`, and `run_boot_test` to gather empirical evidence about the patch's viability.
*   **Output**: A `TestReport` Pydantic model detailing the `overall_status` and granular results for each tool executed.

### 3.6. The Debugger (`debugger.py`)
*   **Role**: The fixer. Activated *only* if the Builder, Reviewer, or Tester fails. 
*   **Flow**: Reads the build logs, test logs, and review feedback. It isolates the technical reason for failure and outputs a `DebugAnalysis` with a `proposed_fix_strategy`. 
*   **Paradigm Shift Trigger**: If the Overseer triggered a Paradigm Shift, the Debugger receives an injected prompt commanding it to propose a radically different fix (e.g., "Stop trying to fix the mutex, disable the feature entirely").

### 3.7. The Overseer (`overseer.py`)
*   **Role**: The programmatic circuit breaker (No LLM calls). 
*   **Flow**: Hashes the critical parts of the state (`patch`, `review_verdict`, `root_cause`). If it detects the exact same state hash 3 times, it recognizes the LLM is stuck in an identical loop.
*   **Action**: Instead of hard-halting, it intercepts the loop, resets the retry counter, sets `is_paradigm_shift = True`, and throws the graph back to the Debugger for a "Hail Mary" attempt. If it fails *again*, it safely halts the graph to protect API token budgets.

---

## 4. Execution & Control Flow (Routing)

The LangGraph `StateGraph` (in `orchestrator.py`) handles execution via conditional edges.

1.  **START** → `jira_ingest` → `planner` → `analyzer` → `builder` → `reviewer`.
2.  **Reviewer Conditional Edge**:
    *   If `APPROVE` → route to `tester`.
    *   If `REQUEST_CHANGES` → route to `debugger`.
3.  **Tester Conditional Edge**:
    *   If `PASS` → route to `finalize` → **END**.
    *   If `FAIL` → route to `debugger`.
4.  **Debugger Edge**:
    *   Always routes to `overseer`.
5.  **Overseer Conditional Edge**:
    *   If `error` (Hard Stop) → route to `escalate` → **END**.
    *   If `paradigm_shift` → route to `debugger` (to inject Hail Mary prompt).
    *   If `clear` → route to `builder` (Retry loop).

---

## 5. Tooling Modules

The tools (`src/tools/`) are LangChain `@tool` decorated functions exposed to the ReAct agents.

*   **`codebase_tools.py`**: Interacts with the local filesystem. Includes `read_file`, `list_directory`, `git_log`. In Phase 3, we added `semantic_search` for RAG capabilities.
*   **`analysis_tools.py`**: Understands C code. Phase 1 used `parse_c_symbols` (Regex). Phase 3 implements `parse_c_ast` (Tree-sitter) for perfect semantic extraction, alongside `find_callers` and `analyze_kconfig` to trace kernel dependency chains.
*   **`build_tools.py` & `test_tools.py`**: Currently mock toolchains (returning simulated `PASS` logs) that simulate `make` and `qemu`. Designed to be seamlessly swapped with Python `subprocess` calls communicating with a Docker daemon in production.
*   **`jira_tools.py`**: Mocks Jira API responses using local JSON profiles.

---

## 6. The Evolution Memory Store

Autonomous agents often solve the same bug multiple times across different hardware revisions. The **Evolution Store** (`src/memory/evolution_store.py`) solves this.

*   **Schema**: A local SQLite database (`evolution.db`) containing `ticket_id`, `subsystem` (e.g., `drivers/spi`), `symptom`, `root_cause`, and `fix_patch`.
*   **Writing**: When the `finalize` node runs successfully, it calls `record_evolution()` to permanently save the patch.
*   **Reading**: When the `jira_ingest` node starts, it calls `query_similar()`. It does a fuzzy text search (or vector search) against the subsystem and symptom, pulling historical fixes into the Planner's initial context window, allowing the agent to "learn" over time.

---

## 7. Deep Dive: AI, LLMs, and LangChain Modules Used

To truly understand how this agent system "thinks" and interacts, it is crucial to understand the specific AI concepts and LangChain classes we rely on.

### 7.1. Base LLM Initialization (`langchain-core.language_models`)
All agents retrieve their brain via `get_llm()` from `src/core/llm.py`. 
*   **`ChatAnthropic` / `ChatOpenAI` / `ChatGoogleGenerativeAI`**: We use the generic `BaseChatModel` interface provided by LangChain. This abstracts away the differences between Anthropic (Claude), OpenAI (GPT), and Google (Gemini).
*   **Why it matters**: Firmware and kernel code often exceed context windows. By using the LangChain abstraction, we can easily swap to models with massive context windows (like Gemini 1.5 Pro or Claude 3.5 Sonnet) simply by changing a `.env` variable, without rewriting any agent logic.

### 7.2. Message Classes (`SystemMessage`, `HumanMessage`)
In traditional prompt engineering, you pass a single giant string. In LangChain, we use message roles:
*   **`SystemMessage`**: Defines the persona and strict rules. For example, in `reviewer.py`, the `SystemMessage` dictates the 6 grading criteria (Concurrency, Memory, Style, etc.). *This is the LLM's immutable constitution.*
*   **`HumanMessage`**: Contains the dynamic state data (the Jira ticket, the codebase snippets, the build logs). 
*   **Why it matters**: Separating these prevents prompt injection and ensures the LLM doesn't lose sight of its prime directive when reading a 10,000-line build log.

### 7.3. Structured Outputs (`.with_structured_output()`)
This is perhaps the most important AI mechanism in the entire project.
*   **The Concept**: Large Language Models naturally output conversational text (e.g., *"Sure! Here is your review. I think it looks good, so I will APPROVE it."*). This breaks programmatic routing.
*   **The LangChain Module**: By chaining `.with_structured_output(PydanticModel)` onto our LLM, we force the underlying provider to use its native "Tool Calling" or "JSON Mode" API. 
*   **The Result**: The LLM is forced to return a strictly typed object. If the schema demands `verdict: Literal["APPROVE", "REQUEST_CHANGES"]`, the LLM physically cannot return conversational filler. This transforms the LLM from a text generator into a deterministic logic gate.

### 7.4. ReAct Agents (`create_react_agent`)
Used heavily in Phase 2 and Phase 3 (Builder, Tester, Analyzer).
*   **The Concept (ReAct)**: Stands for **Re**asoning and **Act**ing. Introduced in a famous 2022 paper, ReAct prompts an LLM to "Think" about what to do, "Act" by calling a tool, and "Observe" the result before thinking again.
*   **The LangGraph Module**: `langgraph.prebuilt.create_react_agent` takes our LLM and a list of Python functions (tools). It compiles them into a mini LangGraph StateGraph behind the scenes.
*   **The Execution**: When the Builder is asked to write a patch, it enters a `create_react_agent` loop. It thinks: *"I need to write a patch"*, it calls the `apply_patch` tool. If the tool returns *"Error: syntax line 40"*, the agent observes this, thinks *"I made a syntax error"*, and loops back to write a new patch.
*   **Recursion Limits**: In Phase 3, we bound this loop using `config={"recursion_limit": 5}` to prevent the agent from burning tokens if it gets confused and loops infinitely.

### 7.5. Tools (`@tool`)
*   **The Concept**: LLMs are frozen in time and cannot interact with the real world. Tools give them "hands."
*   **The LangChain Module**: The `@tool` decorator converts a standard Python function (e.g., `semantic_search`) into a JSON schema that the LLM can understand. It reads the function's docstring and type hints to teach the LLM exactly how and when to use it.
*   **Why it matters**: This allows our Analyzer agent to literally run `git blame` or `grep` on your local hard drive to find bugs, rather than just guessing.

### 7.6. Retrieval-Augmented Generation (RAG)
*   **The Concept**: Passing an entire 30-million-line kernel into the LLM context window is impossible and highly expensive.
*   **The Application**: Our `semantic_search` tool uses RAG. When the agent asks *"Find code related to I2C timeouts"*, we convert that sentence into a vector embedding. We compare it to embeddings of the codebase, pull the top 3 most mathematically relevant code snippets, and feed *only* those snippets into the LLM's `HumanMessage`. This provides perfect context at a fraction of the token cost.
