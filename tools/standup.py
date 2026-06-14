import os
import subprocess

import anthropic

from tools.slack_tool import send_slack_message


def _run(cmd, cwd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd).stdout.strip()


def generate_standup(repo_path: str = None, send_to_slack: bool = False, channel: str = None) -> str:
    path = os.path.expanduser(repo_path) if repo_path else os.getcwd()

    today_log = _run('git log --oneline --since="yesterday 5pm"', path)
    branch = _run("git branch --show-current", path)
    status = _run("git status --short", path)

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=200,
        messages=[{"role": "user", "content": (
            f"Branch: {branch}\n"
            f"Commits since yesterday:\n{today_log or 'None yet today.'}\n\n"
            f"In progress:\n{status or 'Clean.'}\n\n"
            "Write a 3-line Slack standup:\n"
            "Yesterday: ...\nToday: ...\nBlockers: ...\n\n"
            "Plain text, no markdown, casual engineering tone."
        )}]
    )
    standup = resp.content[0].text.strip()

    if send_to_slack and channel:
        result = send_slack_message(channel, standup)
        return f"Standup posted to {channel}."

    return standup
