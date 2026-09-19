import os
import pytest
from tools.security import SecurityError, resolve_safe_path


def test_resolve_safe_path_valid(tmp_path):
    sub = tmp_path / "subdir"
    sub.mkdir()
    f = sub / "test.txt"
    f.write_text("hello")

    res = resolve_safe_path(str(tmp_path), "subdir/test.txt")
    assert os.path.isabs(res)
    assert res == str(f)


def test_resolve_safe_path_current_dir(tmp_path):
    res = resolve_safe_path(str(tmp_path), ".")
    assert res == str(tmp_path)


def test_resolve_safe_path_traversal_blocked(tmp_path):
    with pytest.raises(SecurityError):
        resolve_safe_path(str(tmp_path), "../outside.txt")


def test_resolve_safe_path_absolute_outside_blocked(tmp_path):
    with pytest.raises(SecurityError):
        resolve_safe_path(str(tmp_path), "/etc/passwd")


def test_resolve_safe_path_sneaky_traversal(tmp_path):
    with pytest.raises(SecurityError):
        resolve_safe_path(str(tmp_path), "subdir/../../outside.txt")


def test_resolve_safe_path_symlink_outside_blocked(tmp_path):
    # Create an outside file
    outside_dir = tmp_path.parent / "outside_sandbox"
    outside_dir.mkdir(exist_ok=True)
    outside_file = outside_dir / "secret.txt"
    outside_file.write_text("secret_data")

    # Create a symlink inside the sandbox pointing outside
    sandbox_dir = tmp_path / "sandbox"
    sandbox_dir.mkdir()
    symlink_path = sandbox_dir / "symlink_to_outside"
    os.symlink(str(outside_dir), str(symlink_path))

    # Accessing via symlink should raise SecurityError
    with pytest.raises(SecurityError):
        resolve_safe_path(str(sandbox_dir), "symlink_to_outside/secret.txt")

