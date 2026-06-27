import os
import subprocess


def run_python_file(
    working_directory: str, file_path: str, args: list[str] | None = None
) -> str:
    try:
        working_dir_abs = os.path.abspath(working_directory)
        target_path = os.path.normpath(os.path.join(working_dir_abs, file_path))

        valid_target = (
            os.path.commonpath([working_dir_abs, target_path]) == working_dir_abs
        )

        if not valid_target:
            return f'Error: Cannot execute "{file_path}" as it is outside the permitted working directory'

        if not os.path.isfile(target_path):
            return f'Error: "{file_path}" does not exist or is not a regular file'

        if not file_path.endswith(".py"):
            return f'Error: "{file_path}" is not a Python file'

        command = ["python", target_path]
        if args:
            command.extend(args)

        process = subprocess.run(
            command,
            cwd=working_dir_abs,
            capture_output=True,
            text=True,
            timeout=30,
        )

        output_parts = []

        if process.returncode != 0:
            output_parts.append(f"Process exited with code {process.returncode}")

        if not process.stdout and not process.stderr:
            output_parts.append("No output produced")
        else:
            if process.stdout:
                output_parts.append(f"STDOUT:{process.stdout}")
            if process.stderr:
                output_parts.append(f"STDERR:{process.stderr}")

        return "\n".join(output_parts)

    except Exception as e:
        return f"Error: executing Python file: {e}"
