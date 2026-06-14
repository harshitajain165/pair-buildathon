import os
import subprocess


def run_command(command: str, working_dir: str = None) -> str:
    cwd = os.path.expanduser(working_dir) if working_dir else os.getcwd()
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, cwd=cwd, timeout=60
        )
        out = result.stdout.strip()
        err = result.stderr.strip()

        if result.returncode != 0:
            return f"Exit {result.returncode}: {err or out}"

        return out or "Done."
    except subprocess.TimeoutExpired:
        return "Timed out after 60 seconds."
    except Exception as e:
        return f"Error: {e}"
