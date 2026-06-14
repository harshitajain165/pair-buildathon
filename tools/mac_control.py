import os
import subprocess


def open_application(app_name: str) -> str:
    """Open an app, URL, or file path."""
    # URL
    if app_name.startswith("http://") or app_name.startswith("https://"):
        subprocess.run(["open", app_name])
        return f"Opened {app_name} in browser."

    # File/directory path
    expanded = os.path.expanduser(app_name)
    if os.path.exists(expanded):
        subprocess.run(["open", expanded])
        return f"Opened {app_name}."

    # Mac app by name
    result = subprocess.run(["open", "-a", app_name], capture_output=True, text=True)
    if result.returncode == 0:
        return f"Opened {app_name}."

    # Last resort: plain open (handles many cases)
    result2 = subprocess.run(["open", app_name], capture_output=True, text=True)
    return f"Opened {app_name}." if result2.returncode == 0 else f"Could not open: {app_name}"


def applescript(script: str) -> str:
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    return result.stdout.strip() or result.stderr.strip() or "Done."
