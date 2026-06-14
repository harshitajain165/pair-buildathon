import os
import subprocess

import anthropic


def _run(cmd, cwd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd).stdout.strip()


def _collect_files(path, max_files=40):
    keep_ext = {".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".rb", ".md"}
    skip_dirs = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".next"}
    files = []
    for root, dirs, filenames in os.walk(path):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for fn in filenames:
            if os.path.splitext(fn)[1] in keep_ext:
                files.append(os.path.join(root, fn))
                if len(files) >= max_files:
                    return files
    return files


def summarize_repository(path: str) -> str:
    abs_path = os.path.expanduser(path)
    if not os.path.isdir(abs_path):
        return f"Directory not found: {path}"

    files = _collect_files(abs_path)
    log = _run("git log --oneline -10", abs_path)
    branch = _run("git branch --show-current", abs_path)

    excerpts = []
    for f in files[:12]:
        try:
            with open(f, "r", errors="ignore") as fh:
                content = fh.read(1500)
            rel = os.path.relpath(f, abs_path)
            excerpts.append(f"=== {rel} ===\n{content}")
        except Exception:
            pass

    file_list = "\n".join(os.path.relpath(f, abs_path) for f in files)

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        messages=[{"role": "user", "content": (
            f"Repo: {path} | Branch: {branch}\n\n"
            f"Files:\n{file_list}\n\n"
            f"Recent commits:\n{log}\n\n"
            f"Excerpts:\n{''.join(excerpts[:6])}\n\n"
            "Give a 3-4 sentence spoken summary: what it does, the tech stack, "
            "and the main components. This will be read aloud."
        )}]
    )
    return resp.content[0].text


def catch_me_up(repo_path: str = None) -> str:
    path = os.path.expanduser(repo_path) if repo_path else os.getcwd()

    log = _run("git log --oneline -15", path)
    branch = _run("git branch --show-current", path)
    diff_stat = _run("git diff HEAD~3 --stat 2>/dev/null || git diff --stat", path)
    status = _run("git status --short", path)

    if not log:
        return "No git history found here."

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        messages=[{"role": "user", "content": (
            f"Branch: {branch}\n"
            f"Recent commits:\n{log}\n\n"
            f"Files changed recently:\n{diff_stat}\n\n"
            f"Uncommitted:\n{status or 'none'}\n\n"
            "Give a 3-sentence spoken catch-up for a dev returning after a break. "
            "Lead with the current focus, what was last completed, and what's likely next."
        )}]
    )
    return resp.content[0].text
