# Autonomous AI Software Engineering Agent

An autonomous, multi-turn AI software engineering agent powered by **OpenRouter API** (`openai` client). Engineered according to professional software engineering principles (**SOLID**, **DRY**, **KISS**), the agent autonomously inspects source code, diagnoses bugs and logical discrepancies, applies verified code fixes, and executes unit tests within a strictly sandboxed environment.

---

## Table of Contents

- [Overview](#overview)
- [Harness Engineering (Agent = Model + Harness)](#harness-engineering-agent--model--harness)
- [Architecture & Workflow](#architecture--workflow)
- [Software Engineering Principles](#software-engineering-principles)
- [Core Features](#core-features)
- [Security & Secrets Management](#security--secrets-management)
- [Repository Structure](#repository-structure)
- [Available Agent Tools & Registry](#available-agent-tools--registry)
- [Evaluation Harness & Benchmarks](#evaluation-harness--benchmarks)
- [Ori Harness Integration](#ori-harness-integration)
- [The Target Playground (`calculator/`)](#the-target-playground-calculator)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Environment Configuration](#environment-configuration)
- [Usage Guide](#usage-guide)
  - [Basic Execution](#basic-execution)
  - [Interactive Mode](#interactive-mode)
  - [Verbose & Trace Mode](#verbose--trace-mode)
  - [Replaying Trajectories](#replaying-trajectories)
  - [Budget & Cost Controls](#budget--cost-controls)
  - [Custom Model & Working Directory](#custom-model--working-directory)
- [Running Automated Tests](#running-automated-tests)
- [License](#license)

---

## Overview

Modern software debugging requires iterative reasoning: reading file structures, searching symbols, inspecting implementations, modifying code, and verifying behavior with tests.

This project implements an autonomous **ReAct (Reason + Act)** agent loop:
1. **Formulate Hypothesis**: Analyzes user prompt and repository layout.
2. **Execute Tools**: Dispatches filesystem inspections, file modifications, or subprocess executions via decoupled, registered tools.
3. **Receive Feedback**: Collects stdout, stderr, file contents, and error diagnostics directly into conversational context.
4. **Iterate Autonomously**: Loops (up to a configurable iteration limit, default: 20) until the task is verified and solved.

---

## Harness Engineering (Agent = Model + Harness)

State-of-the-art AI systems recognize that model capability alone is insufficient for autonomous software engineering. The **Agent Harness** provides the operating infrastructure, working memory, security boundaries, and telemetry necessary for high-reliability agentic execution:

1. **Context & Working Memory Harness (`harness/context.py`)**:
   - **`ObservationTrimmer`**: Prevents context explosion by intelligently truncating large observations using a **Head-and-Tail** preservation strategy (preserving initial execution context and final error stack traces).
   - **Compaction**: Dynamically compacts older tool observations when history length threatens context limits.

2. **Loop & Steering Harness (`harness/steering.py`)**:
   - **`LoopDetector`**: Monitors call signatures and automatically halts infinite or repetitive tool loops (e.g. repeating identical arguments 3 times).
   - **Steering Interventions**: Injects high-priority corrective guidance into the turn prompting the model to re-assess hypotheses.
   - **Error Enrichment**: Enriches raw tool failures with actionable hints (e.g. suggesting `search_in_files` when paths are not found).

3. **Sandboxed Tooling Harness (`tools/bash_tool.py`, `tools/git_tool.py`)**:
   - **`bash_command`**: Controlled shell execution with security blacklists (blocking destructive commands like `rm -rf /` or fork bombs) and strict timeout enforcement.
   - **Git State Harness**: `git_status`, `git_diff` for surgical verification, and `git_checkpoint` for rollback snapshots.

4. **Multi-Dimensional Guardrails (`harness/guardrails.py`)**:
   - Enforces ceilings on iterations, total tokens, execution duration (wall-clock time), and estimated dollar cost ($USD).

5. **Telemetry & Trajectory Observability (`harness/telemetry.py`)**:
   - Automatically writes every session trajectory to `.trajectories/<run_id>.jsonl`.
   - Complete replayability for auditing and post-mortem debugging using `python main.py --replay <file>`.

6. **Micro-Evaluation Benchmark Runner (`harness/eval_runner.py`)**:
   - Automated evaluation suite (`evals/tasks.json`) running coding benchmarks against isolated workspaces to score Pass@1, tokens, and cost.

---

## Architecture & Workflow

```
                             +-------------------+
                             |    User Prompt    |
                             +---------+---------+
                                       |
                                       v
                             +-------------------+
                             |      main.py      | (CLI Entrypoint)
                             +---------+---------+
                                       |
                                       v
                             +-------------------+
                             |    Agent Core     |
                    +------->| (agent/core.py)   |<------+
                    |        +---------+---------+       |
                    |                  |                 |
                    |                  v                 |
                    |        +-------------------+       |
         Model      |        |   BaseLLMClient   |       |
       Response     |        | (llm/openrouter.py)       |
                    |        +---------+---------+       |
                    |                  |                 |
                    |                  v                 |
                    |        +-------------------+       |
                    |        |    OpenRouter     |       |
                    |        +---------+---------+       |
                    |                  |                 |
                    |       [Function Call Generated]    |
                    |                  |                 |
                    |                  v                 |
                    |        +-------------------+       |
                    |        |   ToolRegistry    |       |

                    |        | (tools/registry)  |       |
                    |        +---------+---------+       |
                    |                  |                 |
                    |         +--------+--------+        |
                    |         |                 |        |
                    |         v                 v        |
                    |   +-----------+     +-----------+  |
                    |   | FileTools |     | RunPython |  |
                    |   +-----+-----+     +-----+-----+  |
                    |         |                 |        |
                    |         +--------+--------+        |
                    |                  |                 |
                    |                  v                 |
                    |         +-----------------+        |
                    |         | tools/security  |        | (DRY Path Sandboxing)
                    |         +-----------------+        |
                    |                  |                 |
                    +------------------+                 |
                                                         |
                              [Task Solved / Text Output]|
                                       |                 |
                                       v                 |
                             +-------------------+       |
                             |   Final Result    +-------+
                             +-------------------+
```

---

## Software Engineering Principles

The architecture adheres strictly to best-in-class software engineering standards:

* **DRY (Don't Repeat Yourself)**: All path resolution, boundary checks, and sandbox validation are unified inside [`tools/security.py`](tools/security.py). No duplicate validation logic.
* **Single Responsibility (SRP)**:
  - `main.py`: CLI parsing and exit codes only.
  - `agent/core.py`: Conversation orchestration and multi-turn state loop.
  - `llm/`: Model API communication and schema translation.
  - `tools/`: Tool implementation without dependency on LLM orchestration.
* **Open/Closed (OCP)**: Adding a new tool is done by extending `BaseTool` and annotating with `@default_registry.register`. No central dispatch file requires modification.
* **Liskov Substitution & Interface Segregation (LSP & ISP)**: Tools inherit from [`BaseTool`](tools/base.py) with a unified `execute(**kwargs)` interface.
* **Dependency Inversion (DIP)**: The agent depends on the abstract [`BaseLLMClient`](llm/base.py), allowing seamless swapping or mocking of LLM providers for offline testing.

---

## Core Features

- **Autonomous ReAct Loop**: Configurable multi-turn iterations (default: 20) with token tracking and termination safeguards.
- **Dynamic Tool Registry**: Extensible tool registration via class decorator pattern (`@register`).
- **Path Sandboxing (DRY)**: Centralized sandbox protection preventing directory traversal (`../`, absolute path escapes).
- **Execution Safeguards**: Subprocess execution restricted to `.py` files with strict 30-second timeout enforcement.
- **Token Efficiency**: File content automatically truncated at `MAX_CHARS` (default: 10,000 characters) to preserve context limits.
- **Provider Abstraction**: Decoupled LLM client layer enabling easy integration of other providers or local models.
- **Full Test Suite**: 100% automated test coverage using `pytest` with mock-based testing for zero-cost test runs.

---

## Security & Secrets Management

Security is built into the architecture from the ground up:

### 1. API Keys & Credentials
- **No Hardcoded Secrets**: Secrets are loaded from `.env` via `python-dotenv`.
- **Git Protection**: `.gitignore` strictly excludes all `.env*` files.
- **Template Provided**: `.env.example` provides a clean placeholder for required configuration keys.

### 2. Path Traversal & Sandboxing Protection
All filesystem operations are routed through `resolve_safe_path()` in `tools/security.py`:
```python
working_dir_abs = os.path.abspath(working_directory)
target_path = os.path.normpath(os.path.join(working_dir_abs, path))
if os.path.commonpath([working_dir_abs, target_path]) != working_dir_abs:
    raise SecurityError(f'Cannot access "{path}" as it is outside the permitted working directory')
```

### 3. Subprocess Execution Isolation
- Subprocess execution sets `cwd` strictly to the sandboxed working directory.
- Only `.py` files are permitted to execute.
- Strict 30-second timeout prevents infinite execution or denial of service.

---

## Repository Structure

```
aiagent/
├── .env.example               # Template for environment variables (safe to commit)
├── .gitignore                  # Git ignore rules (protects .env, caches, venv)
├── .python-version             # Python version pin (3.10)
├── README.md                   # Comprehensive project documentation
├── pyproject.toml              # Dependencies, packaging, and pytest configuration
├── uv.lock                     # Deterministic dependency lockfile
├── config.py                   # Centralized typed configuration (Config dataclass)
│
├── main.py                     # CLI entrypoint for running the agent
├── prompts.py                  # System instruction prompt for debugging workflows
│
├── agent/                      # Core agent orchestration module
│   ├── __init__.py
│   └── core.py                 # Multi-turn loop, context trimming, loop steering, and budget guards
│
├── harness/                    # Harness Engineering system
│   ├── __init__.py
│   ├── context.py              # ObservationTrimmer (head/tail preservation) and compaction
│   ├── steering.py             # LoopDetector (cycle detection) and error enrichment
│   ├── guardrails.py           # BudgetGuard (iterations, tokens, wall-clock time, cost)
│   ├── telemetry.py            # TrajectoryRecorder (structured JSONL session traces)
│   └── eval_runner.py          # Benchmark evaluation harness runner (pass@1 scoring)
│
├── evals/                      # Reproducible evaluation suites
│   └── tasks.json              # Benchmark tasks for coding agents
│
├── llm/                        # LLM provider abstraction layer (DIP)
│   ├── __init__.py
│   ├── base.py                 # BaseLLMClient abstract interface
│   └── openrouter.py           # OpenRouter API client (OpenAI-compatible)
│
├── tools/                      # Modular tool ecosystem (OCP & DRY)
│   ├── __init__.py
│   ├── base.py                 # BaseTool abstract class
│   ├── registry.py             # ToolRegistry with decorator support (@register)
│   ├── security.py             # Centralized path resolution & sandbox validation
│   ├── file_tools.py           # get_files_info, get_file_content, write_file, edit_file
│   ├── execution_tools.py      # run_python_file with timeout protection
│   ├── search_tools.py         # search_in_files (grep-like file search)
│   ├── bash_tool.py            # bash_command with command blacklist & sandboxing
│   └── git_tool.py             # git_status, git_diff, and git_checkpoint rollback
│
├── tests/                      # Automated test suite (pytest)
│   ├── test_security.py        # Path traversal & sandbox boundary tests
│   ├── test_tools.py           # Tool registration, execution, and boundary tests
│   ├── test_openrouter.py      # OpenRouter client & retry logic tests
│   ├── test_agent.py           # Agent orchestration, mocking, and iteration tests
│   ├── test_harness_context.py # Context trimmer & head/tail preservation tests
│   ├── test_harness_steering.py# Loop detection & error enrichment tests
│   ├── test_bash_tool.py       # Shell execution & blacklist tests
│   ├── test_git_tool.py        # Git diff, status, and checkpoint tests
│   ├── test_guardrails.py      # BudgetGuard ceilings & cost tracking tests
│   ├── test_telemetry.py       # JSONL trajectory recording tests
│   └── test_eval_runner.py     # Evaluation benchmark runner tests
│
└── calculator/                 # Target project (playground for the agent)
    ├── main.py                 # Calculator CLI application
    ├── tests.py                # Unit test suite for calculator operations
    ├── lorem.txt               # Sample text file used for tool testing
    └── pkg/
        ├── calculator.py       # Core calculator logic (infix evaluator)
        ├── render.py           # Output formatter (JSON rendering)
        └── morelorem.txt       # Nested sample text file
```

---

## Available Agent Tools & Registry

All tools inherit from [`BaseTool`](tools/base.py) and are registered automatically with [`default_registry`](tools/registry.py):

| Tool | Parameters | Description | Security Controls |
| :--- | :--- | :--- | :--- |
| `get_files_info` | `directory: str = "."` | Lists directory files, byte sizes, and directory status. | Rejects paths escaping the working directory. |
| `get_file_content` | `file_path: str, start_line: int, end_line: int` | Reads file content with optional line ranges and truncation protection. | Path validation + line bounds + max char limit. |
| `write_file` | `file_path: str, content: str` | Writes or overwrites a file safely. | Path validation + automatic directory creation. |
| `edit_file` | `file_path: str, target_content: str, replacement_content: str` | Surgically edits a unique block of text in a file. | Path validation + uniqueness verification. |
| `search_in_files` | `query: str, directory: str = ".", file_pattern: str = None` | Fast grep-like search across files. | Ignores `.git`, `.venv`, etc. + result limit. |
| `bash_command` | `command: str` | Executes bash commands (tests, linters, git) inside the working directory. | Security blacklist (`rm -rf /`, fork bombs) + timeout + CWD sandboxing. |
| `run_python_file` | `file_path: str, args: list[str] = None` | Executes a Python script in a sandboxed subprocess. | Must be `.py` + timeout + isolated CWD. |
| `git_status` | *(none)* | Inspects working directory git status (`git status --short`). | Read-only working tree query. |
| `git_diff` | `file_path: str = None` | Returns surgical line-by-line patch diff against HEAD. | ObservationTrimmer protection. |
| `git_checkpoint` | `action: str, tag: str = None` | Saves a stash snapshot (`save`) or reverts working directory (`restore`). | Sandboxed to repo working directory. |

---

## Evaluation Harness & Benchmarks

The project comes with a built-in automated **Evaluation Harness** to benchmark agent task success rate (pass@1), token consumption, and cost across coding challenges:

```bash
# Run benchmark in dry-run mode (tests harness isolation without LLM spend)
python -m harness.eval_runner --dry-run

# Run full evaluation benchmark against live model
python -m harness.eval_runner --tasks evals/tasks.json
```

---

## Ori Harness Integration

The agent harness is fully compatible with OpenRouter's official agent harness CLI **Ori**:

```bash
# 1. Install Ori
curl -fsSL https://openrouter.ai/labs/ori/install.sh | bash

# 2. Login via OpenRouter OAuth
ori login

# 3. Run evaluation comparisons across models
ori eval
```

---

## The Target Playground (`calculator/`)

The repository includes a sample project inside `calculator/` that serves as the testing ground for the AI agent:
- **`calculator/pkg/calculator.py`**: An arithmetic evaluator implementing infix evaluation with operator precedence (`+`, `-`, `*`, `/`).
- **`calculator/pkg/render.py`**: Formats calculation results into JSON.
- **`calculator/main.py`**: CLI wrapper accepting expressions such as `"3 + 5 * 2"`.
- **`calculator/tests.py`**: A `unittest` suite covering arithmetic expressions and error conditions.

The agent defaults to `./calculator` as its working directory.

---

## Getting Started

### Prerequisites
- **Python 3.10+**
- An **OpenRouter API Key** (get one at [OpenRouter](https://openrouter.ai/keys))
- (Recommended) **uv** package manager: [https://docs.astral.sh/uv/](https://docs.astral.sh/uv/)

---

### Installation

#### Option A: Using `uv` (Recommended)
```bash
# Clone the repository
git clone https://github.com/maleksn/aiagent.git
cd aiagent

# Install dependencies into virtual environment
uv sync
```

#### Option B: Using Standard `pip` and `venv`
```bash
# Clone the repository
git clone https://github.com/maleksn/aiagent.git
cd aiagent

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install required dependencies
pip install -e .
```

---

### Environment Configuration

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Add your OpenRouter API key inside `.env`:
   ```env
   OPENROUTER_API_KEY="sk-or-v1-your-key-here"
   ```

---

## Usage Guide

### Basic Execution
Run the agent by passing the engineering task description as an argument:

```bash
uv run python main.py "Inspect the calculator project and check if all tests pass."
```

### Interactive Mode
Run the agent in an interactive conversational session:

```bash
uv run python main.py -i
```

### Verbose & Trace Mode
Use the `--verbose` or `--trace` flag to inspect each iteration turn, token counts, tool outputs, and telemetry trajectory paths:

```bash
uv run python main.py "Run tests and summarize findings" --trace
```

### Replaying Trajectories
Audit or replay any past agent run recorded in `.trajectories/`:

```bash
python main.py --replay .trajectories/run_20260919_180000_abc123.jsonl
```

### Budget & Cost Controls
Set hard ceilings on token budgets and estimated dollar costs:

```bash
uv run python main.py "Fix calculator bug" --max-tokens 50000 --max-cost 0.50
```

### Custom Model & Working Directory
You can customize the model and working directory directly via CLI arguments:

```bash
uv run python main.py "Find issues" --working-dir ./calculator --model google/gemini-2.5-flash
```


---

## Running Automated Tests

The project includes a comprehensive, automated test suite built with **`pytest`**:

```bash
# Run all unit tests
uv run pytest

# Run with verbose output
uv run pytest -v
```

### What is tested:
- **Sandbox Security (`tests/test_security.py`)**: Tests path traversal attacks, relative path resolution, and absolute path containment.
- **Tools & Registry (`tests/test_tools.py`)**: Tests tool registration, file reading/writing, size limits, subprocess execution, and error handling.
- **Agent Orchestration (`tests/test_agent.py`)**: Tests the multi-turn agent loop, tool dispatching, iteration limits, and LLM responses using Mock clients (runs offline with zero API costs).

---

## License

This project is licensed under the [MIT License](LICENSE).
