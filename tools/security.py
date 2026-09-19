import os


class SecurityError(Exception):
    """Raised when an operation attempts to access resources outside the permitted sandbox."""
    pass


def resolve_safe_path(working_directory: str, path: str) -> str:
    """
    Safely resolves and validates that a relative or absolute path stays within the working directory.

    Args:
        working_directory: Root folder permitted for file access.
        path: Target file or directory path.

    Returns:
        The normalized absolute target path if valid.

    Raises:
        SecurityError: If target path escapes the permitted working directory.
    """
    working_dir_abs = os.path.abspath(working_directory)
    target_path = os.path.normpath(os.path.join(working_dir_abs, path))

    if os.path.commonpath([working_dir_abs, target_path]) != working_dir_abs:
        raise SecurityError(
            f'Cannot access "{path}" as it is outside the permitted working directory'
        )

    return target_path
