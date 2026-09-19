import os
from tools.bash_tool import BashCommandTool


def test_bash_tool_simple_execution(tmp_path):
    tool = BashCommandTool(timeout_seconds=5)
    test_file = tmp_path / "hello.txt"
    test_file.write_text("hello bash")

    res = tool.execute(working_directory=str(tmp_path), command="cat hello.txt")
    assert "hello bash" in res


def test_bash_tool_blocked_forbidden_command(tmp_path):
    tool = BashCommandTool()
    res = tool.execute(working_directory=str(tmp_path), command="rm -rf /")
    assert "blocked by harness security guardrail" in res


def test_bash_tool_timeout(tmp_path):
    tool = BashCommandTool(timeout_seconds=1)
    res = tool.execute(working_directory=str(tmp_path), command="sleep 3")
    assert "timed out after 1 seconds" in res


def test_bash_tool_exit_code_on_failure(tmp_path):
    tool = BashCommandTool()
    res = tool.execute(working_directory=str(tmp_path), command="ls non_existent_file_xyz")
    assert "Exit code:" in res
    assert "STDERR:" in res
