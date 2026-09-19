# Autonomous AI Software Engineering Agent

An autonomous, multi-turn AI software engineering agent powered by **OpenRouter API** (`openai` client). Engineered according to professional software engineering principles (**SOLID**, **DRY**, **KISS**), the agent autonomously inspects source code, diagnoses bugs and logical discrepancies, applies verified code fixes, and executes unit tests within a strictly sandboxed environment.

---

## Table of Contents

- [Overview](#overview)
- [Architecture & Workflow](#architecture--workflow)
- [Software Engineering Principles](#software-engineering-principles)
- [Core Features](#core-features)
- [Security & Secrets Management](#security--secrets-management)
- [Repository Structure](#repository-structure)
- [Available Agent Tools & Registry](#available-agent-tools--registry)
- [The Target Playground (`calculator/`)](#the-target-playground-calculator)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Environment Configuration](#environment-configuration)
- [Usage Guide](#usage-guide)
  - [Basic Execution](#basic-execution)
  - [Interactive Mode](#interactive-mode)
  - [Verbose Mode](#verbose-mode)
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
│   └── core.py                 # Agent loop, multi-turn context, and token usage
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
│   └── search_tools.py         # search_in_files (grep-like file search)
│
├── tests/                      # Automated test suite (pytest)
│   ├── test_security.py        # Path traversal & sandbox boundary tests
│   ├── test_tools.py           # Tool registration, execution, and boundary tests
│   ├── test_openrouter.py      # OpenRouter client & retry logic tests
│   └── test_agent.py           # Agent orchestration, mocking, and iteration tests
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
| `run_python_file` | `file_path: str, args: list[str] = None` | Executes a Python script in a sandboxed subprocess. | Must be `.py` + 30s timeout + isolated CWD. |

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

### Verbose Mode
Use the `--verbose` flag to inspect each iteration turn, token counts, and tool outputs:

```bash
uv run python main.py "Run tests and summarize findings" --verbose
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
