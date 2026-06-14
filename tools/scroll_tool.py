import subprocess


def _applescript(script: str) -> bool:
    result = subprocess.run(
        ["osascript", "-"],
        input=script,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def scroll_window(direction: str = "down", amount: str = "medium") -> str:
    """
    Scroll the frontmost window.
    direction: up | down | top | bottom
    amount:    small | medium | large  (ignored when direction is top/bottom)
    """
    direction = direction.lower().strip()
    amount    = amount.lower().strip()

    px = {"small": 300, "medium": 700, "large": 1400}.get(amount, 700)

    if direction == "top":
        js = "window.scrollTo(0, 0);"
    elif direction == "bottom":
        js = "window.scrollTo(0, document.body.scrollHeight);"
    elif direction == "up":
        js = f"window.scrollBy(0, -{px});"
    else:
        js = f"window.scrollBy(0, {px});"

    # ── Try browsers via JavaScript injection ────────────────────────────────
    browsers = [
        ("Google Chrome", f'tell application "Google Chrome"\nexecute active tab of front window javascript "{js}"\nend tell'),
        ("Arc",           f'tell application "Arc"\nexecute active tab of front window javascript "{js}"\nend tell'),
        ("Brave Browser", f'tell application "Brave Browser"\nexecute active tab of front window javascript "{js}"\nend tell'),
        ("Safari",        f'tell application "Safari"\ndo JavaScript "{js}" in current tab of front window\nend tell'),
    ]

    for _, script in browsers:
        if _applescript(script):
            return f"Scrolled {direction}."

    # ── Fallback: keyboard shortcuts via System Events ───────────────────────
    if direction == "top":
        # Cmd+Up works in most apps and browsers
        key_script = 'tell application "System Events"\nkey code 126 using command down\nend tell'
    elif direction == "bottom":
        key_script = 'tell application "System Events"\nkey code 125 using command down\nend tell'
    else:
        # Page Up (116) / Page Down (121); repeat for amount
        key_code = 116 if direction == "up" else 121
        repeats  = {"small": 1, "medium": 3, "large": 6}.get(amount, 3)
        lines    = "\n".join([f"key code {key_code}"] * repeats)
        key_script = f'tell application "System Events"\n{lines}\nend tell'

    if _applescript(key_script):
        return f"Scrolled {direction}."

    return f"Could not scroll {direction}. Make sure a window is open and focused."
