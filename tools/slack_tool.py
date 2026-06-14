import os

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


def _client():
    token = os.getenv("SLACK_BOT_TOKEN")
    if not token:
        raise RuntimeError("SLACK_BOT_TOKEN not set in .env")
    return WebClient(token=token)


def send_slack_message(recipient: str, message: str) -> str:
    channel = recipient if recipient.startswith("#") or recipient.startswith("@") else f"@{recipient}"
    try:
        _client().chat_postMessage(channel=channel, text=message)
        return f"Sent to {recipient}."
    except SlackApiError as e:
        return f"Slack error: {e.response['error']}"
    except RuntimeError as e:
        return str(e)


def get_slack_channels() -> str:
    try:
        result = _client().conversations_list(limit=20)
        names = [c["name"] for c in result["channels"]]
        return "Channels: " + ", ".join(names)
    except Exception as e:
        return f"Error: {e}"
