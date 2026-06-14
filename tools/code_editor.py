import os

import anthropic


def edit_file(file_path: str, instruction: str) -> str:
    abs_path = os.path.expanduser(file_path)
    if not os.path.exists(abs_path):
        return f"File not found: {file_path}"

    with open(abs_path, "r", errors="ignore") as f:
        original = f.read()

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8192,
        messages=[{
            "role": "user",
            "content": (
                f"File: {file_path}\n\n"
                f"```\n{original}\n```\n\n"
                f"Instruction: {instruction}\n\n"
                "Return ONLY the complete modified file. No markdown fences, no explanation."
            )
        }]
    )

    new_content = resp.content[0].text.strip()
    if new_content.startswith("```"):
        lines = new_content.split("\n")
        new_content = "\n".join(lines[1:-1]) if lines[-1] == "```" else "\n".join(lines[1:])

    with open(abs_path, "w") as f:
        f.write(new_content)

    return f"Done. {file_path} updated."


def review_changes(repo_path: str = None) -> str:
    """Read git diff and return a voice-friendly code review."""
    import subprocess

    path = os.path.expanduser(repo_path) if repo_path else os.getcwd()
    diff = subprocess.run(
        "git diff HEAD", shell=True, capture_output=True, text=True, cwd=path
    ).stdout

    if not diff.strip():
        diff = subprocess.run(
            "git diff --cached", shell=True, capture_output=True, text=True, cwd=path
        ).stdout

    if not diff.strip():
        return "No uncommitted changes to review."

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[{
            "role": "user",
            "content": (
                f"Git diff:\n```\n{diff[:6000]}\n```\n\n"
                "Give a 3-5 sentence spoken code review. Flag any bugs, missing error handling, "
                "or obvious improvements. Be direct, like a senior engineer."
            )
        }]
    )
    return resp.content[0].text
