import os
import subprocess

import requests


def _headers():
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN not set in .env")
    return {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}


def create_github_issue(repo: str, title: str, body: str = "", labels: list = None) -> str:
    try:
        data = {"title": title, "body": body}
        if labels:
            data["labels"] = labels
        resp = requests.post(
            f"https://api.github.com/repos/{repo}/issues",
            json=data, headers=_headers()
        )
        if resp.status_code == 201:
            issue = resp.json()
            return f"Issue #{issue['number']} created: {issue['html_url']}"
        return f"GitHub error: {resp.json().get('message', 'unknown')}"
    except RuntimeError as e:
        return str(e)


def get_open_prs(repo: str) -> str:
    try:
        resp = requests.get(
            f"https://api.github.com/repos/{repo}/pulls?state=open&per_page=5",
            headers=_headers()
        )
        prs = resp.json()
        if not prs:
            return "No open PRs."
        lines = [f"#{pr['number']}: {pr['title']} by {pr['user']['login']}" for pr in prs]
        return "\n".join(lines)
    except RuntimeError as e:
        return str(e)


def get_current_repo() -> str:
    result = subprocess.run(
        "git remote get-url origin", shell=True, capture_output=True, text=True
    )
    url = result.stdout.strip()
    # Extract owner/repo from git URL
    if "github.com" in url:
        parts = url.replace("https://github.com/", "").replace("git@github.com:", "")
        return parts.rstrip(".git")
    return ""
