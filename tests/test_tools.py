import os
import pytest
from tools.registry import ToolRegistry, default_registry
from tools.base import BaseTool
from tools.file_tools import GetFilesInfoTool, GetFileContentTool, WriteFileTool
from tools.execution_tools import RunPythonFileTool


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
    assert default_registry.has("run_python_file")


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
