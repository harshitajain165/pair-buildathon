"""
Mic → VAD → Pulse STT → Claude (tool use) → Lightning TTS → Speaker
Tool calling is handled by Claude — 100% reliable.
"""

import io
import json
import os
import queue
import struct
import threading
import wave

import anthropic
import pyaudio
import requests

from tools.screen import analyze_screen
from tools.code_editor import edit_file, review_changes
from tools.shell_runner import run_command
from tools.slack_tool import send_slack_message
from tools.git_tool import summarize_repository, catch_me_up
from tools.mac_control import open_application
from tools.spotify_tool import control_spotify
from tools.standup import generate_standup
from tools.ui_modifier import modify_ui
from tools.github_tool import create_github_issue, get_open_prs, create_github_repo
from tools.youtube_tool import play_youtube, control_youtube
from tools.scroll_tool import scroll_window

# ── Smallest AI endpoints ─────────────────────────────────────────────────────
PULSE_URL     = "https://waves-api.smallest.ai/api/v1/pulse/get_text"
LIGHTNING_URL = "https://api.smallest.ai/waves/v1/tts"

# ── Audio ─────────────────────────────────────────────────────────────────────
MIC_RATE  = 16000
MIC_CHUNK = 512      # ~32 ms per chunk
OUT_RATE  = 24000    # Lightning output rate (adjust if needed)

# ── VAD ───────────────────────────────────────────────────────────────────────
SILENCE_RMS      = 500   # tune up if mic picks up background noise
SILENCE_CHUNKS   = 20    # ~640 ms of silence = end of utterance
MIN_SPEECH_CHUNKS = 8    # discard clips shorter than ~256 ms

SYSTEM_PROMPT = (
    "You are Pair, a voice dev assistant.\n"
    "Max 10 words per response. Act immediately — never narrate what you're about to do."
)

CLAUDE_TOOLS = [
    {
        "name": "analyze_screen",
        "description": (
            "Screenshot + Claude vision analysis. Use when user says "
            "'this', 'here', 'what I'm seeing', 'what's on screen', 'explain this'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"question": {"type": "string"}},
            "required": ["question"],
        },
    },
    {
        "name": "edit_file",
        "description": "Read and rewrite a source code file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string"},
                "instruction": {"type": "string"},
            },
            "required": ["file_path", "instruction"],
        },
    },
    {
        "name": "review_changes",
        "description": "Review uncommitted git diff and give spoken code review.",
        "input_schema": {
            "type": "object",
            "properties": {"repo_path": {"type": "string"}},
        },
    },
    {
        "name": "run_command",
        "description": "Run a shell command (git, tests, builds, installs).",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "working_dir": {"type": "string"},
            },
            "required": ["command"],
        },
    },
    {
        "name": "send_slack_message",
        "description": "Send a Slack message. recipient = person name or #channel.",
        "input_schema": {
            "type": "object",
            "properties": {
                "recipient": {"type": "string"},
                "message": {"type": "string"},
            },
            "required": ["recipient", "message"],
        },
    },
    {
        "name": "summarize_repository",
        "description": "Spoken summary of a git repo: what it does, stack, key files.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    {
        "name": "open_application",
        "description": (
            "Open a Mac app, URL, or folder path. "
            "e.g. 'Slack', 'https://github.com', '~/Desktop/pair'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"app_name": {"type": "string"}},
            "required": ["app_name"],
        },
    },
    {
        "name": "generate_standup",
        "description": "Generate standup from recent git commits, optionally post to Slack.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo_path": {"type": "string"},
                "send_to_slack": {"type": "boolean"},
                "channel": {"type": "string"},
            },
        },
    },
    {
        "name": "control_spotify",
        "description": "Control Spotify playback.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["play", "pause", "next", "previous", "current_track",
                             "search", "volume_up", "volume_down"],
                },
                "query": {"type": "string", "description": "Song/artist for search"},
            },
            "required": ["action"],
        },
    },
    {
        "name": "modify_ui",
        "description": (
            "Modify the visual UI of a web app: colors, fonts, spacing, layout, dark mode. "
            "Takes a screenshot, then edits the CSS."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "instruction": {"type": "string"},
                "project_path": {"type": "string"},
            },
            "required": ["instruction"],
        },
    },
    {
        "name": "catch_me_up",
        "description": "Summarize what the developer was last working on via git history.",
        "input_schema": {
            "type": "object",
            "properties": {"repo_path": {"type": "string"}},
        },
    },
    {
        "name": "create_github_issue",
        "description": "Create a GitHub issue in a repository.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo": {"type": "string", "description": "owner/repo"},
                "title": {"type": "string"},
                "body": {"type": "string"},
                "labels": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["repo", "title"],
        },
    },
    {
        "name": "create_github_repo",
        "description": (
            "Create a new GitHub repository. Use when the user says "
            "'create a repo', 'make a new GitHub repo', 'initialize a repo called X'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name":        {"type": "string", "description": "Repository name (no spaces)"},
                "description": {"type": "string", "description": "Short description"},
                "private":     {"type": "boolean", "description": "True for private, false for public"},
                "auto_init":   {"type": "boolean", "description": "Initialize with a README (default true)"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "get_open_prs",
        "description": "List open pull requests in a GitHub repository.",
        "input_schema": {
            "type": "object",
            "properties": {"repo": {"type": "string", "description": "owner/repo"}},
            "required": ["repo"],
        },
    },
    {
        "name": "play_youtube",
        "description": (
            "Open YouTube and search for a video. Use when the user says "
            "'play', 'put on', 'search YouTube', 'watch', or names a video/song/channel."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "search query"}},
            "required": ["query"],
        },
    },
    {
        "name": "scroll_window",
        "description": (
            "Scroll the frontmost window or browser tab. Use when the user says "
            "'scroll down', 'scroll up', 'go to the top', 'go to the bottom', "
            "'scroll a bit', 'scroll a lot'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "direction": {
                    "type": "string",
                    "enum": ["down", "up", "top", "bottom"],
                },
                "amount": {
                    "type": "string",
                    "enum": ["small", "medium", "large"],
                    "description": "How far to scroll. Ignored when direction is top/bottom.",
                },
            },
            "required": ["direction"],
        },
    },
    {
        "name": "control_youtube",
        "description": (
            "Pause or resume a YouTube video currently playing in the browser. "
            "Use when the user says 'pause', 'stop the video', 'resume', 'unpause'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["pause", "play", "resume"],
                }
            },
            "required": ["action"],
        },
    },
]

TOOL_HANDLERS = {
    "analyze_screen":      analyze_screen,
    "edit_file":           edit_file,
    "review_changes":      review_changes,
    "run_command":         run_command,
    "send_slack_message":  send_slack_message,
    "summarize_repository": summarize_repository,
    "open_application":    open_application,
    "generate_standup":    generate_standup,
    "control_spotify":     control_spotify,
    "modify_ui":           modify_ui,
    "catch_me_up":         catch_me_up,
    "create_github_issue": create_github_issue,
    "create_github_repo":  create_github_repo,
    "get_open_prs":        get_open_prs,
    "play_youtube":        play_youtube,
    "control_youtube":     control_youtube,
    "scroll_window":       scroll_window,
}


def _rms(data: bytes) -> float:
    count = len(data) // 2
    if not count:
        return 0.0
    shorts = struct.unpack(f"{count}h", data)
    return (sum(s * s for s in shorts) / count) ** 0.5


class PairClient:
    def __init__(self, overlay=None, voice_id: str = "olivia"):
        self.overlay   = overlay
        self._audio    = pyaudio.PyAudio()
        self._out_q    = queue.Queue()
        self._running  = False
        self._lock     = threading.Lock()   # guards _history
        self._history  = []
        self._claude      = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self._api_key     = os.getenv("SMALLEST_API_KEY")
        self._out_rate    = OUT_RATE
        self._voice_id    = voice_id
        self._processing  = False   # True while STT→Claude→TTS is in-flight

    def _set_status(self, s: str):
        if self.overlay:
            self.overlay.set_status(s)

    # ── TTS ──────────────────────────────────────────────────────────────────

    def _tts(self, text: str):
        print(f"[tts] {text}")
        try:
            resp = requests.post(
                LIGHTNING_URL,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "text": text,
                    "voice_id": self._voice_id,
                    "model": "lightning_v3.1",
                    "speed": 1.0,
                    "sample_rate": OUT_RATE,
                    "language": "en",
                    "output_format": "wav",
                },
                timeout=30,
            )
            print(f"[tts] status={resp.status_code}  len={len(resp.content)}")
            if resp.status_code == 200:
                audio = resp.content
                # Response is always WAV — strip header before queuing raw PCM
                if audio[:4] == b"RIFF":
                    buf = io.BytesIO(audio)
                    with wave.open(buf) as wf:
                        actual_rate = wf.getframerate()
                        audio = wf.readframes(wf.getnframes())
                    # Restart playback stream if sample rate changed
                    if actual_rate != self._out_rate:
                        self._out_rate = actual_rate
                for i in range(0, len(audio), 4096):
                    self._out_q.put(audio[i:i + 4096])
            else:
                print(f"  body={resp.text[:300]!r}")
        except Exception as e:
            print(f"[tts exception] {e}")

    # ── Playback ─────────────────────────────────────────────────────────────

    def _play_worker(self):
        stream = self._audio.open(
            format=pyaudio.paInt16, channels=1,
            rate=self._out_rate, output=True, frames_per_buffer=1024
        )
        while self._running:
            try:
                chunk = self._out_q.get(timeout=0.1)
                stream.write(chunk)
            except queue.Empty:
                pass
        stream.stop_stream()
        stream.close()

    # ── STT ──────────────────────────────────────────────────────────────────

    def _transcribe(self, frames: list) -> str:
        raw = b"".join(frames)
        # Build WAV bytes in memory
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(MIC_RATE)
            wf.writeframes(raw)
        wav_bytes = buf.getvalue()
        try:
            resp = requests.post(
                PULSE_URL,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/octet-stream",
                },
                params={"language": "en"},
                data=wav_bytes,
                timeout=30,
            )
            print(f"[stt] status={resp.status_code}  body={resp.text[:200]!r}")
            if resp.status_code == 200:
                data = resp.json()
                return data.get("transcription", "").strip()
            else:
                return ""
        except Exception as e:
            print(f"[stt exception] {e}")
            return ""

    # ── Claude turn ───────────────────────────────────────────────────────────

    def _process(self, transcript: str):
        if not transcript.strip():
            return
        print(f"[user] {transcript}")
        self._set_status("thinking")

        with self._lock:
            self._history.append({"role": "user", "content": transcript})
            messages = list(self._history)

        while True:
            resp = self._claude.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                tools=CLAUDE_TOOLS,
                messages=messages,
            )
            messages.append({"role": "assistant", "content": resp.content})

            if resp.stop_reason == "tool_use":
                tool_results = []
                for block in resp.content:
                    if block.type == "tool_use":
                        self._set_status(f"running {block.name}")
                        print(f"[tool] {block.name}  args={json.dumps(block.input)[:120]}")
                        result = self._call_tool(block.name, block.input)
                        print(f"[result] {str(result)[:200]}")
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": str(result),
                        })
                messages.append({"role": "user", "content": tool_results})
            else:
                reply = "".join(
                    b.text for b in resp.content if hasattr(b, "text")
                ).strip()
                with self._lock:
                    self._history = messages
                if reply:
                    self._set_status("speaking")
                    self._tts(reply)
                break

        self._set_status("ready")

    def _call_tool(self, name: str, args: dict) -> str:
        handler = TOOL_HANDLERS.get(name)
        if not handler:
            return f"Unknown tool: {name}"
        try:
            return handler(**args)
        except Exception as e:
            return f"Error in {name}: {e}"

    # ── VAD mic loop ─────────────────────────────────────────────────────────

    def _mic_loop(self):
        stream = self._audio.open(
            format=pyaudio.paInt16, channels=1,
            rate=MIC_RATE, input=True, frames_per_buffer=MIC_CHUNK
        )
        self._set_status("ready")
        print("Pair ready. Start talking.\n")

        in_speech     = False
        silent_count  = 0
        frames        = []

        try:
            while self._running:
                data = stream.read(MIC_CHUNK, exception_on_overflow=False)
                loud = _rms(data) > SILENCE_RMS

                if loud:
                    if not in_speech:
                        in_speech    = True
                        silent_count = 0
                        while not self._out_q.empty():
                            try: self._out_q.get_nowait()
                            except: break
                        self._set_status("listening")
                    frames.append(data)
                    silent_count = 0
                else:
                    if in_speech:
                        frames.append(data)
                        silent_count += 1
                        if silent_count >= SILENCE_CHUNKS:
                            in_speech = False
                            if len(frames) >= MIN_SPEECH_CHUNKS and not self._processing:
                                self._processing = True
                                self._set_status("thinking")
                                captured, frames = frames, []
                                threading.Thread(
                                    target=self._handle_utterance,
                                    args=(captured,),
                                    daemon=True,
                                ).start()
                            else:
                                frames = []
        finally:
            stream.stop_stream()
            stream.close()

    def _handle_utterance(self, frames: list):
        try:
            text = self._transcribe(frames)
            if text:
                self._process(text)
            else:
                self._set_status("ready")
        finally:
            self._processing = False

    # ── Entry point ───────────────────────────────────────────────────────────

    async def run(self):
        import asyncio
        self._running = True

        threading.Thread(target=self._play_worker, daemon=True).start()

        # Greeting
        threading.Thread(target=self._tts, args=("Hey.",), daemon=True).start()

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._mic_loop)
