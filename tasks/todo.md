# Tasks: Harness Engineering

## Task 1: Context Trimmer and Working Memory
**Description:** Implement `harness/context.py` containing `ObservationTrimmer` to handle large tool outputs intelligently (preserving head lines and tail error traces) and manage token limits without hard cuts.
**Acceptance criteria:**
- [x] Trims output exceeding character/token threshold cleanly without breaking lines
- [x] Preserves first N and last M lines (head and tail) with a clear truncation note
- [x] Provides token usage estimator
**Verification:**
- [x] `pytest tests/test_harness_context.py` passes
**Dependencies:** None
**Files touched:**
- `harness/context.py`
- `tests/test_harness_context.py`
**Status:** Completed

---

## Task 2: Loop & Stuck Detection
**Description:** Implement `harness/steering.py` with `LoopDetector` to identify repeated identical tool calls or cyclical errors and generate guidance intervention messages.
**Acceptance criteria:**
- [x] Tracks call signatures (tool_name + args)
- [x] Triggers loop alert when threshold (e.g. 3 consecutive identical calls) is met
- [x] Enriches tool errors with constructive tips
**Verification:**
- [x] `pytest tests/test_harness_steering.py` passes
**Dependencies:** None
**Files touched:**
- `harness/steering.py`
- `tests/test_harness_steering.py`
**Status:** Completed

---

## Task 3: Core Agent Loop Harness Integration
**Description:** Update `Agent.run` in `agent/core.py` to seamlessly leverage the context trimmer and loop detector, injecting intervention messages when stuck.
**Acceptance criteria:**
- [x] Replaces raw string slicing with `ObservationTrimmer`
- [x] Intercepts infinite loops and notifies the model instead of silently burning iterations
- [x] Keeps backwards compatibility with existing `Agent` parameters
**Verification:**
- [x] `pytest tests/test_agent.py` passes with 100% existing tests passing + new loop tests
**Dependencies:** Task 1, Task 2
**Files touched:**
- `agent/core.py`
- `tests/test_agent.py`
**Status:** Completed

---

## Checkpoint 1: Context & Steering
- [x] `pytest tests/test_agent.py tests/test_harness_context.py tests/test_harness_steering.py` passes clean

---

## Task 4: Sandboxed Bash Execution Tool
**Description:** Implement `tools/bash_tool.py` providing a safe, controlled `BashCommandTool` with working directory sandboxing, timeout enforcement, output streaming/truncation, and security blacklist.
**Acceptance criteria:**
- [x] Executes shell commands safely inside `working_directory`
- [x] Blocks forbidden commands (e.g., `rm -rf /`, `:(){ :|:& };:`, altering system root)
- [x] Enforces configurable timeout
**Verification:**
- [x] `pytest tests/test_bash_tool.py` passes
**Dependencies:** None
**Files touched:**
- `tools/bash_tool.py`
- `tests/test_bash_tool.py`
**Status:** Completed

---

## Task 5: Git State & Diff Harness Tool
**Description:** Implement `tools/git_tool.py` allowing the agent to inspect `git diff`, `git status`, and create lightweight rollback checkpoints before/after risky actions.
**Acceptance criteria:**
- [x] `git_status` and `git_diff` tools return readable diffs
- [x] Safety checkpoint/revert capability within the working directory
**Verification:**
- [x] `pytest tests/test_git_tool.py` passes
**Dependencies:** None
**Files touched:**
- `tools/git_tool.py`
- `tests/test_git_tool.py`
**Status:** Completed

---

## Task 6: Tool Registration & System Prompt Update
**Description:** Register the new tools in `tools/__init__.py` and `tools/registry.py`, and update `prompts.py` to guide the model on when and how to use bash, tests, and git diffs.
**Acceptance criteria:**
- [x] New tools are automatically available in `default_registry`
- [x] System prompt reflects modern engineering workflow: inspect -> plan -> implement -> run tests via bash -> inspect diff
**Verification:**
- [x] `pytest tests/test_tools.py` passes
**Dependencies:** Task 4, Task 5
**Files touched:**
- `tools/__init__.py`
- `tools/registry.py`
- `prompts.py`
- `tests/test_tools.py`
**Status:** Completed

---

## Checkpoint 2: Execution & Tooling
- [x] All tool and security tests pass: `pytest tests/`

---

## Task 7: Budget & Guardrail Policies
**Description:** Implement `harness/guardrails.py` with multi-dimensional budget tracking (tokens, cost estimation, max execution time) and safety enforcement.
**Acceptance criteria:**
- [x] Halts execution if token, cost, or time ceiling is breached with clean `AgentResult` error
- [x] Computes estimated cost using OpenRouter pricing rates
**Verification:**
- [x] `pytest tests/test_guardrails.py` passes
**Dependencies:** Task 3
**Files touched:**
- `harness/guardrails.py`
- `agent/core.py`
- `tests/test_guardrails.py`
**Status:** Completed

---

## Task 8: Trajectory Observability & Replay
**Description:** Implement `harness/telemetry.py` to record every turn, tool call, duration, token usage, and outcome to `.trajectories/<run_id>.jsonl` with an inspection/replay helper.
**Acceptance criteria:**
- [x] Structured JSONL written on every agent run
- [x] Contains all steps, tool calls, and performance metrics
- [x] Adds `--trace` / `--replay` support in `main.py`
**Verification:**
- [x] `pytest tests/test_telemetry.py` passes
**Dependencies:** Task 7
**Files touched:**
- `harness/telemetry.py`
- `main.py`
- `tests/test_telemetry.py`
**Status:** Completed

---

## Task 9: Evaluation Harness & Benchmark Suite
**Description:** Create a reproducible evaluation harness `harness/eval_runner.py` with micro-benchmark coding tasks (`evals/tasks.json`), scoring pass@1, speed, and cost.
**Acceptance criteria:**
- [x] Benchmark runner executes defined coding tasks in isolated subdirectories
- [x] Validates automated test suite pass/fail
- [x] Generates summary report with Pass Rate, Total Cost, and Token Usage
**Verification:**
- [x] `python -m harness.eval_runner --dry-run` and `pytest tests/test_eval_runner.py`
**Dependencies:** Task 8
**Files touched:**
- `harness/eval_runner.py`
- `evals/tasks.json`
- `tests/test_eval_runner.py`
**Status:** Completed

---

## Task 10: Documentation & Ori Harness Integration
**Description:** Update `README.md` and document how to run the agent with Ori (`ori claude` / `ori codex`) and run eval benchmarks (`ori eval`).
**Acceptance criteria:**
- [x] README updated with Harness Engineering features, CLI arguments, and architecture diagram
- [x] Documentation for running evaluations and using Ori Harness
**Verification:**
- [x] Documentation review and validation
**Dependencies:** Tasks 1-9
**Files touched:**
- `README.md`
**Status:** Completed

---

## Final Checkpoint: Full Harness Verification
- [x] All unit and harness test suites verified
- [x] Full end-to-end dry run verified
