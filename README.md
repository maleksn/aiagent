# Autonomous AI Software Engineering Agent

An autonomous, multi-turn AI software engineering agent powered by the **Google GenAI SDK** (`google-genai`) and Google's **Gemini 2.5 Flash** model. The agent is engineered to autonomously inspect source code, diagnose bugs and logical discrepancies, apply verified code fixes, and run unit tests within a securely sandboxed environment.

---

## Table of Contents

- [Overview](#overview)
- [Architecture & Workflow](#architecture--workflow)
- [Core Features](#core-features)
- [Security & Secrets Management](#security--secrets-management)
- [Repository Structure](#repository-structure)
- [Available Agent Tools](#available-agent-tools)
- [The Target Playground (`calculator/`)](#the-target-playground-calculator)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Environment Configuration](#environment-configuration)
- [Usage Guide](#usage-guide)
  - [Basic Execution](#basic-execution)
  - [Verbose Mode](#verbose-mode)
  - [Standard Python Execution](#standard-python-execution)
- [Running Tests](#running-tests)
- [License](#license)

---

## Overview

Modern software debugging requires iterative reasoning: reading file structures, inspecting implementations, analyzing mathematical and logical precedence, modifying code, and verifying behavior with tests.

This project implements a complete **ReAct (Reason + Act)** autonomous agent loop. When provided with a user prompt, the agent:
1. Formulates a step-by-step hypothesis.
2. Interacts with the filesystem and executes commands via dedicated function calls (tools).
3. Receives execution outputs and errors as feedback in its conversational context.
4. Iterates autonomously (up to 20 turns) until the task is completely solved.

---

## Architecture & Workflow

```
                             +-------------------+
                             |    User Prompt    |
                             +---------+---------+
                                       |
                                       v
                             +-------------------+
                   +-------->| Gemini 2.5 Flash  |<---------+
                   |         |  (GenAI Client)   |          |
                   |         +---------+---------+          |
                   |                   |                    |
        Function   |       [Function Call Generated]        |
        Response   |                   |                    |
        Feedback   |                   v                    |
                   |         +-------------------+          |
                   |         | call_function.py  |          |
                   |         |  (Dispatcher &    |          |
                   |         | Sandboxed Scope)  |          |
                   |         +---------+---------+          |
                   |                   |                    |
                   |                   v                    |
                   |       +-----------------------+        |
                   |       |   Functions Library   |        |
                   |       | - get_files_info      |        |
                   |       | - get_file_content    |        |
                   |       | - write_file          |        |
                   |       | - run_python_file     |        |
                   |       +-----------+-----------+        |
                   |                   |                    |
                   +-------------------+                    |
                                                            |
                             [No more tool calls / Finished]|
                                       |                    |
                                       v                    |
                             +-------------------+          |
                             |   Final Report    +----------+
                             +-------------------+
```

### Agent Step-by-Step Cycle
1. **User Request**: Initial prompt passed via CLI to `main.py`.
2. **Context Assembly**: Prompt combined with a strict `system_prompt` from `prompts.py` enforcing systematic debugging.
3. **Model Generation**: Gemini 2.5 Flash determines whether to invoke tools or produce the final response.
4. **Tool Execution**: Tool calls dispatched to `call_function.py`, enforcing sandboxed relative paths inside `./calculator`.
5. **Observation Loop**: Execution results (stdout, file content, errors) fed back into the conversation context as role `user` / `tool` parts.
6. **Resolution**: Once satisfied, the model returns a direct summary without function calls and finishes execution.

---

## Core Features

- **Autonomous ReAct Loop**: Supports up to 20 multi-turn iterations with full history tracking.
- **Strict Methodological Prompting**: The system prompt (`prompts.py`) enforces:
  1. *Locate*: Explore directory layout before guessing.
  2. *Inspect*: Read actual code completely; never assume implementations.
  3. *Analyze*: Reason through logic, data structures, and operator precedence rules.
  4. *Fix*: Apply targeted, permanent fixes.
  5. *Verify*: Execute tests and ensure clean state.
- **Deterministic Evaluation**: Runs with `temperature=0` for predictable, reproducible engineering tasks.
- **Path Sandboxing**: Built-in defense against path traversal (`../`, absolute paths, etc.) ensuring all operations remain inside the target directory.
- **Execution Safeguards**: Subprocess execution is restricted to `.py` files with strict 30-second timeouts.
- **Token Efficiency**: File reads are automatically capped at `MAX_CHARS` (10,000 characters) to prevent context exhaustion.

---

## Security & Secrets Management

Security is a primary focus of this project:

### 1. API Keys & Credentials
- **No Hardcoded Keys**: No API keys, credentials, or tokens are committed to source control.
- **Environment Isolation**: The application loads credentials from `.env` via `python-dotenv`.
- **Git Protection**: `.gitignore` is configured to ignore all `.env*` files, preventing accidental commits or pushes to remote repositories.
- **Template Provided**: `.env.example` provides a clean, key-free template for developers.

### 2. Path Traversal & Sandboxing Protection
Every filesystem tool uses canonical path validation:
```python
working_dir_abs = os.path.abspath(working_directory)
target_path = os.path.normpath(os.path.join(working_dir_abs, file_path))
valid_target = os.path.commonpath([working_dir_abs, target_path]) == working_dir_abs
```
Attempts to escape the working directory (e.g., `../../etc/passwd` or `/bin/cat`) are immediately rejected.

### 3. Subprocess Execution Isolation
- Commands run with `cwd=working_dir_abs`.
- Only `.py` files can be executed.
- Subprocesses timeout after 30 seconds to prevent infinite loops or hanging processes.

---

## Repository Structure

```
aiagent/
├── .env.example               # Template for environment variables (safe to commit)
├── .gitignore                  # Git ignore rules (protects .env, caches, venv)
├── .python-version             # Python version pin (3.10)
├── README.md                   # Project documentation
├── pyproject.toml              # Project dependencies and packaging metadata
├── uv.lock                     # Deterministic dependency lockfile
│
├── main.py                     # CLI entrypoint and agent ReAct loop
├── prompts.py                  # System instruction prompt for the autonomous agent
├── call_function.py            # Function declarations & dispatcher for Gemini tools
├── config.py                   # Global configuration settings (MAX_CHARS limit)
│
├── functions/                  # Tool implementations exposed to Gemini
│   ├── get_files_info.py       # Lists directory contents, sizes, and file types
│   ├── get_file_content.py     # Reads file content with size limits and truncation
│   ├── write_file.py           # Creates or overwrites files safely
│   └── run_python_file.py      # Executes Python files within a sandboxed subprocess
│
├── calculator/                 # Target project (playground for the agent)
│   ├── main.py                 # Calculator CLI application
│   ├── tests.py                # Unit test suite for calculator operations
│   ├── lorem.txt               # Sample text file used for tool testing
│   └── pkg/
│       ├── calculator.py       # Core calculator logic (infix evaluator)
│       ├── render.py           # Output formatter (JSON rendering)
│       └── morelorem.txt       # Nested sample text file
│
└── test_*.py                   # Tool boundary & security verification tests
    ├── test_get_files_info.py  # Tests directory listing and traversal blocking
    ├── test_get_file_content.py# Tests file reading, truncation, and path safety
    ├── test_run_python_file.py # Tests Python execution, args, and timeout safety
    └── test_write_file.py      # Tests safe file writing and permission boundaries
```

---

## Available Agent Tools

The agent has access to four tools registered in `call_function.py`:

| Tool | Parameters | Description | Security Controls |
| :--- | :--- | :--- | :--- |
| `get_files_info` | `directory: str = "."` | Lists files, sizes, and directory status. | Rejects paths outside working directory. |
| `get_file_content` | `file_path: str` | Reads file content as plain text. | Path validation + 10,000 character truncation. |
| `write_file` | `file_path: str`, `content: str` | Writes or overwrites a file. | Path validation + directory creation safety. |
| `run_python_file` | `file_path: str`, `args: list[str]` | Executes a Python file in a subprocess. | Must end with `.py` + 30s timeout + isolated CWD. |

---

## The Target Playground (`calculator/`)

The repository includes a self-contained sample project inside `calculator/` that serves as the testing ground for the AI agent:
- **`calculator/pkg/calculator.py`**: An arithmetic evaluator implementing infix evaluation with operator precedence (`+`, `-`, `*`, `/`).
- **`calculator/pkg/render.py`**: Formats calculation results into formatted JSON.
- **`calculator/main.py`**: CLI wrapper accepting expressions such as `"3 + 5 * 2"`.
- **`calculator/tests.py`**: A `unittest` suite covering arithmetic expressions and error conditions.

The agent is directed by default to `./calculator` as its working directory, allowing it to autonomously discover issues, run tests, fix logic bugs (e.g., precedence mistakes), and verify fixes.

---

## Getting Started

### Prerequisites
- **Python 3.10+**
- A **Google Gemini API Key** (available free from [Google AI Studio](https://aistudio.google.com/))
- (Recommended) **uv** package manager: [https://docs.astral.sh/uv/](https://docs.astral.sh/uv/)

---

### Installation

#### Option A: Using `uv` (Recommended)
Fast, reproducible dependency resolution using `uv.lock`:
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
pip install google-genai==1.12.1 python-dotenv==1.1.0
```

---

### Environment Configuration

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Open `.env` and add your Gemini API key:
   ```env
   GEMINI_API_KEY="AIzaSyYourActualAPIKeyHere"
   ```

> [!IMPORTANT]
> Never commit your `.env` file to version control. The repository's `.gitignore` automatically prevents `.env` files from being tracked.

---

## Usage Guide

### Basic Execution
Run the agent by providing a task description as an argument:

```bash
uv run python main.py "Inspect the calculator project and check if all tests pass."
```

Or ask the agent to find and fix bugs:

```bash
uv run python main.py "Investigate the calculator codebase, fix any operator precedence bugs, and verify with tests."
```

### Verbose Mode
Use the `--verbose` flag to view iteration tokens, individual tool invocations, and function responses:

```bash
uv run python main.py "Run tests and summarize findings" --verbose
```

### Standard Python Execution
If you are using an activated virtual environment instead of `uv`:
```bash
python main.py "Inspect the calculator project" --verbose
```

---

## Running Tests

### 1. Tool Security & Boundary Tests
Run the test scripts to verify path sandboxing, boundary restrictions, and truncation handling:

```bash
# Test file reader and truncation limit
uv run python test_get_file_content.py

# Test directory listing and path traversal blocking
uv run python test_get_files_info.py

# Test Python runner, argument passing, and timeout safeguards
uv run python test_run_python_file.py

# Test safe file writing
uv run python test_write_file.py
```

### 2. Calculator Target Application Tests
Run unit tests for the target calculator application directly:

```bash
uv run python calculator/tests.py
```

---

## Security Audit Checklist

Before pushing changes or deploying:
- [x] `.env` is listed in `.gitignore` and not tracked by Git.
- [x] No API keys or credentials appear in commit history.
- [x] Path traversal protections are active on all filesystem tools.
- [x] Subprocess execution limits (timeout & extension checks) are enforced.
- [x] `.env.example` contains only placeholder values.

---

## License

This project is licensed under the [MIT License](LICENSE) (or your chosen repository license).
