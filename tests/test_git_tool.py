import subprocess
from tools.git_tool import GitStatusTool, GitDiffTool, GitCheckpointTool


def _init_git_repo(path):
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "agent@test.local"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Agent Test"], cwd=path, check=True, capture_output=True)
    init_file = path / "initial.txt"
    init_file.write_text("initial")
    subprocess.run(["git", "add", "."], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, check=True, capture_output=True)


def test_git_status_and_diff(tmp_path):
    _init_git_repo(tmp_path)
    status_tool = GitStatusTool()
    diff_tool = GitDiffTool()

    # Initial state clean
    clean_res = status_tool.execute(working_directory=str(tmp_path))
    assert "clean" in clean_res.lower()

    # Modify file
    (tmp_path / "initial.txt").write_text("modified content")
    dirty_res = status_tool.execute(working_directory=str(tmp_path))
    assert "initial.txt" in dirty_res

    # Diff
    diff_res = diff_tool.execute(working_directory=str(tmp_path))
    assert "+modified content" in diff_res
    assert "-initial" in diff_res


def test_git_checkpoint_restore(tmp_path):
    _init_git_repo(tmp_path)
    checkpoint_tool = GitCheckpointTool()

    # Add a file and save checkpoint
    (tmp_path / "bad_change.txt").write_text("broken")
    restore_res = checkpoint_tool.execute(working_directory=str(tmp_path), action="restore")
    assert "successfully restored" in restore_res
    assert not (tmp_path / "bad_change.txt").exists()
