import asyncio
import base64
import json
import os
import queue
import threading

import pyaudio
import websockets

from tools.screen import analyze_screen
from tools.code_editor import edit_file, review_changes
from tools.shell_runner import run_command
from tools.slack_tool import send_slack_message
from tools.git_tool import summarize_repository, catch_me_up
from tools.mac_control import open_application
from tools.spotify_tool import control_spotify
from tools.standup import generate_standup
from tools.ui_modifier import modify_ui
from tools.github_tool import create_github_issue, get_open_prs

HYDRA_URL = "wss://api.smallest.ai/waves/v1/s2s"

MIC_RATE = 16000
MIC_CHUNK = 1024
OUT_RATE = 48000

SYSTEM_PROMPT = """You are Pair, a voice dev assistant.

On startup: say only "Hey." Nothing else. Do not list capabilities.

Always: max 10 words per response. Do things, don't describe doing them."""

TOOLS = [
    {
        "name": "analyze_screen",
        "description": (
            "Take a screenshot and analyze it with Claude vision. "
            "Use whenever the user says 'this', 'here', 'what I'm seeing', 'what's wrong', "
            "'explain this', or references anything currently visible on screen."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "What to look for or answer about the screen"}
            },
            "required": ["question"]
        }
    },
    {
        "name": "edit_file",
        "description": "Read and edit a source code file. Can add functions, fix bugs, refactor, add imports, modify styles.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Absolute or relative path to the file"},
                "instruction": {"type": "string", "description": "What to change"}
            },
            "required": ["file_path", "instruction"]
        }
    },
    {
        "name": "review_changes",
        "description": "Review git diff before pushing. Gives a spoken code review of uncommitted changes.",
        "parameters": {
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "description": "Path to the repo (optional)"}
            }
        }
    },
    {
        "name": "run_command",
        "description": "Run a shell command. Use for git, tests, builds, package installs, etc.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "working_dir": {"type": "string", "description": "Directory to run in (optional)"}
            },
            "required": ["command"]
        }
    },
    {
        "name": "send_slack_message",
        "description": "Send a Slack message. recipient can be a person's name or #channel.",
        "parameters": {
            "type": "object",
            "properties": {
                "recipient": {"type": "string"},
                "message": {"type": "string"}
            },
            "required": ["recipient", "message"]
        }
    },
    {
        "name": "summarize_repository",
        "description": "Give a spoken summary of a git repository: what it does, the stack, and key components.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the repository root"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "open_application",
        "description": "Open a Mac app, URL, or folder path. Pass URLs like 'https://github.com' directly. Pass folder paths like '~/Desktop'. Pass app names like 'Slack', 'Figma', 'Spotify'.",
        "parameters": {
            "type": "object",
            "properties": {
                "app_name": {"type": "string", "description": "App name, full URL, or file/folder path"}
            },
            "required": ["app_name"]
        }
    },
    {
        "name": "generate_standup",
        "description": "Generate a standup from recent git commits. Optionally post it to Slack.",
        "parameters": {
            "type": "object",
            "properties": {
                "repo_path": {"type": "string"},
                "send_to_slack": {"type": "boolean"},
                "channel": {"type": "string", "description": "Slack channel to post to (e.g. #standup)"}
            }
        }
    },
    {
        "name": "control_spotify",
        "description": "Control Spotify: play, pause, next, previous, current_track, volume_up, volume_down, or search.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["play", "pause", "next", "previous", "current_track", "search", "volume_up", "volume_down"]
                },
                "query": {"type": "string", "description": "Song or artist (for search only)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "modify_ui",
        "description": (
            "Modify the visual UI of a web app being built. "
            "Takes a screenshot, understands the current UI, then edits the CSS/stylesheet. "
            "Use for: change colors, fonts, spacing, layout, dark mode, etc."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "instruction": {"type": "string", "description": "The visual change to make"},
                "project_path": {"type": "string", "description": "Path to the project root (optional)"}
            },
            "required": ["instruction"]
        }
    },
    {
        "name": "catch_me_up",
        "description": "Summarize what the developer was last working on using git history and branch state.",
        "parameters": {
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "description": "Path to the repo (optional, defaults to cwd)"}
            }
        }
    },
    {
        "name": "create_github_issue",
        "description": "Create a GitHub issue in a repository.",
        "parameters": {
            "type": "object",
            "properties": {
                "repo": {"type": "string", "description": "owner/repo format"},
                "title": {"type": "string"},
                "body": {"type": "string"},
                "labels": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["repo", "title"]
        }
    },
    {
        "name": "get_open_prs",
        "description": "List open pull requests in a GitHub repository.",
        "parameters": {
            "type": "object",
            "properties": {
                "repo": {"type": "string", "description": "owner/repo format"}
            },
            "required": ["repo"]
        }
    }
]

TOOL_HANDLERS = {
    "analyze_screen": analyze_screen,
    "edit_file": edit_file,
    "review_changes": review_changes,
    "run_command": run_command,
    "send_slack_message": send_slack_message,
    "summarize_repository": summarize_repository,
    "open_application": open_application,
    "generate_standup": generate_standup,
    "control_spotify": control_spotify,
    "modify_ui": modify_ui,
    "catch_me_up": catch_me_up,
    "create_github_issue": create_github_issue,
    "get_open_prs": get_open_prs,
}


class HydraClient:
    def __init__(self, overlay=None):
        self.overlay = overlay
        self._audio = pyaudio.PyAudio()
        self._out_queue: queue.Queue = queue.Queue()
        self._running = False
        self.ws = None
        self._session_ready = False  # simple boolean, no asyncio.Event (avoids Python 3.9 loop bug)

    def _set_status(self, status: str):
        if self.overlay:
            self.overlay.set_status(status)

    async def _configure_session(self):
        wrapped = [{"type": "function", **t} for t in TOOLS]
        payload = {
            "type": "session.configure",
            "session": {
                "instructions": SYSTEM_PROMPT,
                "voice": "sloane",
                "tools": wrapped,
            }
        }
        print(f"[configure] sending session.configure with {len(wrapped)} tools")
        await self.ws.send(json.dumps(payload))

    async def _stream_mic(self):
        print("[mic] streaming started")

        stream = self._audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=MIC_RATE,
            input=True,
            frames_per_buffer=MIC_CHUNK
        )
        try:
            while self._running:
                data = stream.read(MIC_CHUNK, exception_on_overflow=False)
                await self.ws.send(json.dumps({
                    "type": "input_audio_buffer.append",
                    "audio": base64.b64encode(data).decode()
                }))
                await asyncio.sleep(0)
        finally:
            stream.stop_stream()
            stream.close()

    def _play_worker(self):
        stream = self._audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=OUT_RATE,
            output=True,
            frames_per_buffer=1024
        )
        while self._running:
            try:
                chunk = self._out_queue.get(timeout=0.1)
                stream.write(chunk)
            except queue.Empty:
                continue
        stream.stop_stream()
        stream.close()

    async def _dispatch_tool(self, name: str, args: dict) -> str:
        handler = TOOL_HANDLERS.get(name)
        if not handler:
            return f"Unknown tool: {name}"
        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(None, lambda: handler(**args))
        except Exception as e:
            return f"Tool error in {name}: {e}"

    async def _schedule_response_create(self):
        """Debounced response.create — waits 200ms so multi-tool turns don't fire early."""
        await asyncio.sleep(0.2)
        await self.ws.send(json.dumps({"type": "response.create"}))

    async def _handle_messages(self):
        pending: dict[str, dict] = {}       # call_id -> {name, args}
        response_create_task = None          # debounce handle

        async for raw in self.ws:
            event = json.loads(raw)
            etype = event.get("type", "")
            print(f"[event] {etype}")

            if etype == "session.configured":
                self._session_ready = True
                self._set_status("ready")
                print("Pair is ready. Start talking.")
                print(f"[session.configured] full response: {json.dumps(event)[:500]}")

            elif etype == "input_audio_buffer.speech_started":
                # Drain output queue so it shuts up the moment user speaks
                while not self._out_queue.empty():
                    try:
                        self._out_queue.get_nowait()
                    except Exception:
                        break
                self._set_status("listening")

            elif etype == "input_audio_buffer.speech_stopped":
                self._set_status("thinking")

            elif etype == "response.output_audio.delta":
                audio = event.get("delta", "")
                if audio:
                    self._out_queue.put(base64.b64decode(audio))
                    self._set_status("speaking")

            elif etype == "response.done":
                self._set_status("ready")

            elif etype == "response.function_call_arguments.delta":
                cid = event.get("call_id", "")
                name = event.get("name", "")
                if cid not in pending:
                    pending[cid] = {"name": name, "args": ""}
                pending[cid]["args"] += event.get("delta", "")

            elif etype == "response.function_call_arguments.done":
                cid = event.get("call_id", "")
                name = pending.get(cid, {}).get("name") or event.get("name", "")
                args_str = pending.pop(cid, {}).get("args") or event.get("arguments", "")

                self._set_status(f"running {name}")
                print(f"[tool] {name}({args_str[:120]})")

                try:
                    args = json.loads(args_str) if args_str.strip() else {}
                except json.JSONDecodeError:
                    args = {}

                result = await self._dispatch_tool(name, args)
                print(f"[tool result] {result[:200]}")

                await self.ws.send(json.dumps({
                    "type": "conversation.item.create",
                    "item": {
                        "type": "function_call_output",
                        "call_id": cid,
                        "output": str(result)
                    }
                }))

                # Debounced response.create — cancel previous if another tool just fired
                if response_create_task and not response_create_task.done():
                    response_create_task.cancel()
                response_create_task = asyncio.create_task(self._schedule_response_create())

            elif etype == "error":
                code = event.get("error", {}).get("code", "")
                msg  = event.get("error", {}).get("message", "")
                print(f"[hydra error] {code}: {msg}")

    async def run(self):
        self._session_ready = False
        api_key = os.getenv("SMALLEST_API_KEY")
        url = f"{HYDRA_URL}?model=hydra&api_key={api_key}"
        self._running = True

        play_thread = threading.Thread(target=self._play_worker, daemon=True)
        play_thread.start()

        async with websockets.connect(url) as ws:
            self.ws = ws
            await self._configure_session()
            await asyncio.gather(
                self._stream_mic(),
                self._handle_messages()
            )
