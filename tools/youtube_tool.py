import subprocess
import urllib.parse


def play_youtube(query: str) -> str:
    """Open YouTube in the default browser and search for a video."""
    url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(query)
    subprocess.run(["open", url], check=False)
    return f"Opened YouTube for: {query}"


def _applescript(script: str) -> bool:
    result = subprocess.run(
        ["osascript", "-"],
        input=script,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def control_youtube(action: str) -> str:
    """Pause, play, or resume YouTube in the browser."""
    action = action.lower().strip()

    if action in ("pause", "stop"):
        js = "var v=document.querySelector('video');if(v){v.pause();}"
        verb = "paused"
    elif action in ("play", "resume", "unpause"):
        js = "var v=document.querySelector('video');if(v){v.play();}"
        verb = "resumed"
    else:
        return f"Unknown action '{action}'. Supported: pause, play, resume."

    # Try common browsers in order
    browsers = [
        ("Google Chrome", f'tell application "Google Chrome"\nexecute active tab of front window javascript "{js}"\nend tell'),
        ("Arc",           f'tell application "Arc"\nexecute active tab of front window javascript "{js}"\nend tell'),
        ("Brave Browser", f'tell application "Brave Browser"\nexecute active tab of front window javascript "{js}"\nend tell'),
        ("Safari",        f'tell application "Safari"\ndo JavaScript "{js}" in current tab of front window\nend tell'),
    ]

    for name, script in browsers:
        if _applescript(script):
            return f"YouTube {verb}."

    # Fallback: send Space key — works if browser window is focused
    if _applescript('tell application "System Events"\nkey code 49\nend tell'):
        return f"YouTube {verb} (space key sent)."

    return "Could not control YouTube. Make sure a browser window is open."
