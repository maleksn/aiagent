import os
import pytest
from tools.registry import ToolRegistry, default_registry
from tools.base import BaseTool
from tools.file_tools import GetFilesInfoTool, GetFileContentTool, WriteFileTool, EditFileTool
from tools.execution_tools import RunPythonFileTool
from tools.search_tools import SearchInFilesTool



def test_registry_registration():
    registry = ToolRegistry()

    class CustomTool(BaseTool):
        name = "custom_tool"
        description = "A custom tool for testing"
        parameters_schema = {"type": "object"}

        def execute(self, **kwargs) -> str:
            return "custom result"

    tool = registry.register(CustomTool)
    assert registry.has("custom_tool")
    assert isinstance(registry.get("custom_tool"), CustomTool)
    assert registry.execute("custom_tool") == "custom result"
    assert "Error: Unknown tool" in registry.execute("non_existent")


def test_default_registry_has_core_tools():
    assert default_registry.has("get_files_info")
    assert default_registry.has("get_file_content")
    assert default_registry.has("write_file")
    assert default_registry.has("edit_file")
    assert default_registry.has("run_python_file")
    assert default_registry.has("search_in_files")



def test_registry_to_tools_format():
    tools = default_registry.to_tools()
    assert isinstance(tools, list)
    assert len(tools) >= 4
    for tool in tools:
        assert tool["type"] == "function"
        fn = tool["function"]
        assert "name" in fn
        assert "description" in fn
        assert "parameters" in fn
        assert isinstance(fn["parameters"], dict)


def test_write_and_read_file(tmp_path):
    write_tool = WriteFileTool()
    read_tool = GetFileContentTool()

    # Write file
    res_write = write_tool.execute(
        working_directory=str(tmp_path),
        file_path="sub/hello.txt",
        content="Hello, World!",
    )
    assert "Successfully wrote" in res_write

    # Read file
    res_read = read_tool.execute(
        working_directory=str(tmp_path),
        file_path="sub/hello.txt",
    )
    assert res_read == "Hello, World!"

    # Read non-existent
    res_not_found = read_tool.execute(
        working_directory=str(tmp_path),
        file_path="sub/does_not_exist.txt",
    )
    assert "Error: File not found" in res_not_found


def test_get_files_info(tmp_path):
    tool = GetFilesInfoTool()
    (tmp_path / "file1.txt").write_text("abc")
    (tmp_path / "folder").mkdir()

    res = tool.execute(working_directory=str(tmp_path), directory=".")
    assert "file1.txt" in res
    assert "file_size=3 bytes" in res
    assert "folder: file_size=" in res
    assert "is_dir=True" in res


def test_run_python_file(tmp_path):
    run_tool = RunPythonFileTool()
    script = tmp_path / "script.py"
    script.write_text('import sys\nprint("OUTPUT:" + " ".join(sys.argv[1:]))\n')

    res = run_tool.execute(
        working_directory=str(tmp_path),
        file_path="script.py",
        args=["arg1", "arg2"],
    )
    assert "OUTPUT:arg1 arg2" in res


def test_tools_security_rejection(tmp_path):
    read_tool = GetFileContentTool()
    write_tool = WriteFileTool()

    read_res = read_tool.execute(working_directory=str(tmp_path), file_path="../secret.txt")
    assert "outside the permitted working directory" in read_res

    write_res = write_tool.execute(
        working_directory=str(tmp_path), file_path="/tmp/outside.txt", content="hack"
    )
    assert "outside the permitted working directory" in write_res


def test_get_file_content_line_range(tmp_path):
    tool = GetFileContentTool()
    f = tmp_path / "numbered.txt"
    f.write_text("line 1\nline 2\nline 3\nline 4\nline 5\n")

    res = tool.execute(
        working_directory=str(tmp_path),
        file_path="numbered.txt",
        start_line=2,
        end_line=4,
    )
    assert "2: line 2" in res
    assert "3: line 3" in res
    assert "4: line 4" in res
    assert "1: line 1" not in res
    assert "5: line 5" not in res


def test_edit_file(tmp_path):
    edit_tool = EditFileTool()
    f = tmp_path / "code.py"
    f.write_text("def add(a, b):\n    return a - b\n")

    # Success edit
    res = edit_tool.execute(
        working_directory=str(tmp_path),
        file_path="code.py",
        target_content="return a - b",
        replacement_content="return a + b",
    )
    assert "Successfully edited" in res
    assert f.read_text() == "def add(a, b):\n    return a + b\n"

    # Target not found
    res_not_found = edit_tool.execute(
        working_directory=str(tmp_path),
        file_path="code.py",
        target_content="return non_existent",
        replacement_content="pass",
    )
    assert "Error: target_content not found" in res_not_found

    # Multiple matches ambiguity
    f.write_text("foo bar foo")
    res_multiple = edit_tool.execute(
        working_directory=str(tmp_path),
        file_path="code.py",
        target_content="foo",
        replacement_content="baz",
    )
    assert "appears 2 times" in res_multiple


def test_search_in_files(tmp_path):
    search_tool = SearchInFilesTool()
    (tmp_path / "a.py").write_text("def find_me():\n    pass\n")
    (tmp_path / "b.txt").write_text("just some text\nfind_me here too\n")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "c.py").write_text("def other():\n    # find_me inside sub\n    return 1\n")

    # Search all
    res = search_tool.execute(
        working_directory=str(tmp_path),
        query="find_me",
    )
    assert "a.py:1:" in res
    assert "b.txt:2:" in res
    assert "sub/c.py:2:" in res

    # Search with pattern filter
    res_filtered = search_tool.execute(
        working_directory=str(tmp_path),
        query="find_me",
        file_pattern="*.py",
    )
    assert "a.py:1:" in res_filtered
    assert "b.txt" not in res_filtered
    assert "sub/c.py:2:" in res_filtered

