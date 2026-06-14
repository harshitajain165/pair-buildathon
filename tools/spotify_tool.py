import subprocess
import urllib.parse


def control_spotify(action: str, query: str = None) -> str:
    def applescript(s):
        r = subprocess.run(["osascript", "-e", s], capture_output=True, text=True)
        return r.stdout.strip()

    if action == "search" and query:
        encoded = urllib.parse.quote(query)
        subprocess.run(["open", f"spotify:search:{encoded}"])
        return f"Searching Spotify for '{query}'."

    scripts = {
        "play":          'tell application "Spotify" to play',
        "pause":         'tell application "Spotify" to pause',
        "next":          'tell application "Spotify" to next track',
        "previous":      'tell application "Spotify" to previous track',
        "current_track": (
            'tell application "Spotify" to '
            'return (name of current track) & " by " & (artist of current track)'
        ),
        "volume_up":     'tell application "Spotify" to set sound volume to (sound volume + 10)',
        "volume_down":   'tell application "Spotify" to set sound volume to (sound volume - 10)',
    }

    script = scripts.get(action)
    if not script:
        return f"Unknown Spotify action: {action}"

    out = applescript(script)
    return out if action == "current_track" else f"Spotify: {action}."
