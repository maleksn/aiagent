# Implementation Plan: Harness Engineering for AI Coding Agent

## Overview
Transform the autonomous coding agent from a basic LLM wrapper into a robust, industrial-grade agent harness (**Agent = Model + Harness**). 
This harness provides context management (smart observation truncation and compaction), execution sandboxing (controlled Bash command execution, Git diff/checkpointing), loop & stuck detection (preventing cycling and infinite loops), guardrails (token/cost/time budgets and safety policies), trajectory observability (structured JSONL logging for debugging and replay), and an evaluation harness (micro-eval benchmark suite + Ori harness integration).

## Architecture Decisions
- **Modularity under `harness/`**: Centralize all harness capabilities in a dedicated `harness/` package to keep `agent/core.py` clean, extensible, and decoupled.
- **Pillar-based Structure**:
  1. `harness/context.py`: Smart observation truncation (head + tail preserving error trace) and sliding window context compaction.
  2. `harness/steering.py`: Loop detection (detecting identical repeated tool calls) and actionable error enrichment.
  3. `harness/guardrails.py`: Multi-dimensional budgets (iterations, tokens, wall-clock time, cost) and tool safety levels (READ_ONLY, MUTATING, DANGEROUS).
  4. `harness/sandbox.py` & Tools: Controlled `BashCommandTool` with security blacklist, timeout, and `GitTool` for diffs and rollback checkpoints.
  5. `harness/telemetry.py`: Structured JSONL trajectory recording for every session.
  6. `harness/eval_runner.py`: Reproducible micro-benchmark evaluation harness to measure pass@1 and cost.
- **Backwards Compatibility**: The existing `Agent.run()` interface remains fully functional with sensible defaults while accepting the new harness configuration.

## Task List

### Phase 1: Context & Steering Harness (Working Memory & Self-Correction)
- [ ] Task 1: Implement `harness/context.py` with `ObservationTrimmer` and Token Budget Tracking.
- [ ] Task 2: Implement `harness/steering.py` with `LoopDetector` and intelligent error hints.
- [ ] Task 3: Integrate context trimming and loop intervention into `agent/core.py`.

### Checkpoint: Context & Steering
- [ ] All unit tests pass; agent intercepts repetitive loops and gracefully truncates massive tool outputs.

### Phase 2: Sandboxed Execution & Tooling Harness
- [ ] Task 4: Implement `tools/bash_tool.py` (`BashCommandTool`) with sandboxing, command blacklisting, and timeout.
- [ ] Task 5: Implement `tools/git_tool.py` (`GitDiffTool`, `GitStatusTool`, `GitCheckpoint`) for workspace state management.
- [ ] Task 6: Register new tools in `tools/registry.py` and update `prompts.py` with updated tool documentation and guidelines.

### Checkpoint: Execution & Tooling
- [ ] Bash and Git tools are verified with security tests (path traversal protection and command injection prevention).

### Phase 3: Guardrails, Telemetry & Evaluation Harness
- [ ] Task 7: Implement `harness/guardrails.py` (token limits, wall-clock timeout, cost tracking).
- [ ] Task 8: Implement `harness/telemetry.py` (structured trajectory logging to `.trajectories/` and replay capability).
- [ ] Task 9: Implement `harness/eval_runner.py` with a micro-eval task suite (`evals/tasks.json`) and test against `calculator`.
- [ ] Task 10: Document Ori harness integration and CLI flags (`--trace`, `--benchmark`, `--eval`) in `main.py` and `README.md`.

### Checkpoint: Complete System
- [ ] Full test suite passes.
- [ ] End-to-end evaluation runs on micro-benchmark with recorded trajectories.

## Risks and Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| Bash execution security escape | High | Strict path sandboxing, forbidden command blacklist, subprocess timeouts, and environment isolation. |
| Context truncation dropping critical info | Medium | Head + Tail truncation strategy (keeps initial command/file start and final error stack trace). |
| Performance overhead from telemetry | Low | Asynchronous or fast buffered JSONL writing. |
