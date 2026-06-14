import base64
import io
import os
import subprocess

import anthropic
import mss
from PIL import Image


def _find_style_files(path):
    skip = {"node_modules", ".git", "dist", "build", ".next"}
    style_exts = {".css", ".scss", ".sass", ".less"}
    results = []
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in skip]
        for f in files:
            if os.path.splitext(f)[1] in style_exts:
                results.append(os.path.join(root, f))
    return results


def modify_ui(instruction: str, project_path: str = None) -> str:
    path = os.path.expanduser(project_path) if project_path else os.getcwd()

    # Screenshot current state
    with mss.mss() as sct:
        shot = sct.grab(sct.monitors[1])
        img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        img_b64 = base64.standard_b64encode(buf.getvalue()).decode()

    # Find style files
    style_files = _find_style_files(path)
    if not style_files:
        return "No CSS/SCSS files found. Check your project path."

    # Prefer the first global stylesheet (app.css, globals.css, index.css, styles.css)
    priority = ["globals", "global", "app", "main", "index", "styles", "style"]
    target = style_files[0]
    for keyword in priority:
        match = next((f for f in style_files if keyword in os.path.basename(f).lower()), None)
        if match:
            target = match
            break

    with open(target, "r", errors="ignore") as f:
        existing = f.read()

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": img_b64}},
                {
                    "type": "text",
                    "text": (
                        f"The screenshot shows the current state of the web app.\n\n"
                        f"UI change requested: {instruction}\n\n"
                        f"Target stylesheet: {os.path.relpath(target, path)}\n\n"
                        f"Current content:\n```\n{existing[:4000]}\n```\n\n"
                        "Return ONLY the complete updated stylesheet. No explanation, no fences."
                    )
                }
            ]
        }]
    )

    new_css = resp.content[0].text.strip()
    if new_css.startswith("```"):
        lines = new_css.split("\n")
        new_css = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    with open(target, "w") as f:
        f.write(new_css)

    # Trigger browser refresh via AppleScript (Chrome or Safari)
    subprocess.run(
        ["osascript", "-e",
         'tell application "Google Chrome" to tell active tab of front window to reload'],
        capture_output=True
    )

    return f"UI updated in {os.path.basename(target)}. Browser refreshed."
