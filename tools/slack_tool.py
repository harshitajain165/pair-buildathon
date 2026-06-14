import os

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


def _client():
    token = os.getenv("SLACK_BOT_TOKEN")
    if not token:
        raise RuntimeError("SLACK_BOT_TOKEN not set in .env")
    return WebClient(token=token)


def send_slack_message(recipient: str, message: str) -> str:
    """
    Send a Slack message.
    - recipient starting with '#'  → post to that channel
    - anything else                → look up the person by name and open a DM
    """
    client = _client()
    try:
        if recipient.startswith("#"):
            channel_id = recipient
        else:
            # Find user by display name / real name / username
            name = recipient.lstrip("@").lower().strip()
            resp = client.users_list(limit=500)
            user_id = None
            for member in resp.get("members", []):
                if member.get("deleted") or member.get("is_bot"):
                    continue
                profile = member.get("profile", {})
                display = profile.get("display_name", "").lower()
                real    = profile.get("real_name", "").lower()
                uname   = member.get("name", "").lower()
                if (name == display or name == real or name == uname
                        or display.startswith(name) or real.startswith(name)
                        or name in real or name in display):
                    user_id = member["id"]
                    break

            if not user_id:
                return (f"Could not find a Slack user matching '{recipient}'. "
                        "Check the spelling or use a #channel name instead.")

            dm = client.conversations_open(users=[user_id])
            channel_id = dm["channel"]["id"]

        client.chat_postMessage(channel=channel_id, text=message)
        return f"Message sent to {recipient}."

    except SlackApiError as e:
        err = e.response.get("error", "unknown")
        if err == "missing_scope":
            return ("Slack bot is missing required scopes. "
                    "Go to api.slack.com/apps → your app → OAuth & Permissions "
                    "and add: users:read, im:write, chat:write.")
        return f"Slack error: {err}"
    except RuntimeError as e:
        return str(e)


def get_slack_channels() -> str:
    try:
        result = _client().conversations_list(limit=20)
        names = [c["name"] for c in result["channels"]]
        return "Channels: " + ", ".join(names)
    except Exception as e:
        return f"Error: {e}"
