# Pair

**Pair** is a voice-first AI developer assistant for macOS. Speak naturally — Pair understands context, executes actions across your machine and the tools you use every day, and responds in a human voice. No typing required.

---

## Capabilities

### Developer Workflow
- Analyze what's on your screen and explain it
- Read, edit, and write source files by voice instruction
- Run shell commands, build scripts, and test suites
- Review uncommitted git diffs and surface issues aloud
- Summarize any repository — stack, structure, key files
- Catch you up on what you were last working on via git history
- Generate daily standup from recent commits, optionally post to Slack

### GitHub
- Create repositories (public or private)
- Open issues with title, body, and labels
- List open pull requests on any repo

### Communication
- Send Slack DMs to any teammate by name
- Post to any Slack channel

### Media & Browser
- Search and open YouTube videos by voice
- Pause and resume YouTube playback
- Scroll any browser tab or native window — up, down, to top, to bottom

### System Control
- Open any macOS application, folder, or URL
- Control Spotify — play, pause, skip, search, volume
- Modify UI of web projects — colors, layout, dark mode — via screenshot + CSS edit

---

## System Architecture

```
  ┌──────────────────────────────────────────────────────────────────┐
  │                          PAIR  SESSION                           │
  │                                                                  │
  │  ┌─────────────────┐                       ┌──────────────────┐ │
  │  │  AUDIO CAPTURE  │                       │  AUDIO PLAYBACK  │ │
  │  │                 │                       │                  │ │
  │  │  PyAudio 16kHz  │                       │  PCM queue       │ │
  │  │  RMS-based VAD  │                       │  PyAudio 24kHz   │ │
  │  │  Frame buffer   │                       │  Barge-in flush  │ │
  │  └────────┬────────┘                       └────────▲─────────┘ │
  │           │                                         │            │
  │           ▼                                         │            │
  │  ┌─────────────────┐                       ┌────────┴─────────┐ │
  │  │  PULSE STT API  │                       │  LIGHTNING TTS   │ │
  │  │                 │                       │                  │ │
  │  │  Smallest AI    │                       │  Smallest AI     │ │
  │  │  WAV → text     │                       │  text → WAV      │ │
  │  │  REST (octet)   │                       │  lightning_v3.1  │ │
  │  └────────┬────────┘                       └────────▲─────────┘ │
  │           │                                         │            │
  │           ▼                                         │            │
  │  ┌──────────────────────────────────────────────────┴─────────┐ │
  │  │                    INTELLIGENCE LAYER                       │ │
  │  │                                                             │ │
  │  │   Claude claude-sonnet-4-6  ──  tool_use loop              │ │
  │  │   ┌─────────────────────────────────────────────────────┐  │ │
  │  │   │  System prompt  │  Conversation history  │  Tools   │  │ │
  │  │   └─────────────────────────────────────────────────────┘  │ │
  │  │                          │                                  │ │
  │  │             stop_reason = "tool_use"?                       │ │
  │  │                  ╱               ╲                          │ │
  │  │               yes                 no ──▶ TTS reply          │ │
  │  │                │                                            │ │
  │  │                ▼                                            │ │
  │  │   ┌─────────────────────────────────────────────────────┐  │ │
  │  │   │                  TOOL EXECUTION LAYER               │  │ │
  │  │   │                                                     │  │ │
  │  │   │  Vision & Screen      analyze_screen                │  │ │
  │  │   │  Code & Files         edit_file · review_changes    │  │ │
  │  │   │  Shell & Git          run_command · summarize_repo  │  │ │
  │  │   │                       catch_me_up · generate_standup│  │ │
  │  │   │  GitHub REST API      create_repo · create_issue    │  │ │
  │  │   │                       get_open_prs                  │  │ │
  │  │   │  Slack Web API        send_message (DM + channel)   │  │ │
  │  │   │  Media & Browser      play_youtube · control_youtube│  │ │
  │  │   │                       control_spotify               │  │ │
  │  │   │  macOS Automation     open_application · modify_ui  │  │ │
  │  │   │                       scroll_window                 │  │ │
  │  │   └────────────────────────────┬────────────────────────┘  │ │
  │  │                                │ tool_result                │ │
  │  │                                └──────────▶ back to Claude  │ │
  │  └─────────────────────────────────────────────────────────────┘ │
  │                                                                  │
  │  ┌──────────────────────┐    ┌───────────────────────────────┐  │
  │  │    FLOATING WIDGET   │    │         LANDING PAGE          │  │
  │  │                      │    │                               │  │
  │  │  PyQt6 frameless     │    │  FastAPI + static HTML        │  │
  │  │  Always-on-top pill  │    │  Persona picker (5 voices)    │  │
  │  │  Siri gradient orb   │    │  Voice preview (CDN audio)    │  │
  │  │  Frosted glass UI    │    │  POST /start → launch_queue   │  │
  │  │  30 fps animation    │    │  localhost:8421               │  │
  │  └──────────────────────┘    └───────────────────────────────┘  │
  └──────────────────────────────────────────────────────────────────┘
```

### Layer Breakdown

**Audio Pipeline**
Microphone audio is captured at 16 kHz in 32 ms chunks. A lightweight energy-based VAD (RMS threshold) detects speech onset and silence. On silence, the captured frames are encoded as WAV in-memory and dispatched to Pulse STT over a single REST call. TTS audio is returned as WAV, decoded, and streamed to the speaker via a PCM queue — decoupled from the intelligence loop so responses play while the next turn can already begin capturing.

**Intelligence Layer**
Claude receives the full conversation history and a registry of 14 tool schemas. It responds in a `tool_use` loop: if a tool is requested, Pair executes it, appends the result to the message history, and calls Claude again — repeating until `stop_reason` is `end_turn`. The final text reply is sent to TTS. A `_processing` flag ensures only one utterance is in-flight at a time, preventing mic echo from triggering a second response during playback.

**Tool Execution Layer**
Tools are thin wrappers around system calls, REST APIs, and AppleScript. Each is registered with a JSON Schema that Claude uses to decide when and how to invoke it. Adding a new capability is a single file addition plus schema registration — no changes to the core pipeline.

**UI Layer**
The landing page (FastAPI + HTML) runs on localhost and handles persona selection. On launch, it enqueues the selected `voice_id` and the Qt main loop picks it up, initializes the floating widget and client, and starts the audio pipeline in a background thread. The widget communicates with the client thread via Qt signals to keep all paint operations on the main thread.

### Scalability Notes

| Concern | Current | Path to Scale |
|---|---|---|
| Multi-user | Single session per process | Each session is a self-contained `PairClient` — spawn N processes or move to async workers |
| STT / TTS latency | Single blocking REST call | Smallest AI APIs are stateless — add a connection pool or switch to streaming endpoints |
| Tool execution | Sequential within a turn | Independent tools in a single Claude turn can be parallelized with `ThreadPoolExecutor` |
| Conversation memory | In-process list | Drop-in replacement: persist history to SQLite or Redis keyed by session ID |
| New tools | One file + schema registration | Tool registry can be loaded dynamically from a directory — hot-reload without restart |
| Cross-platform | macOS only (AppleScript) | Swap AppleScript layer for Windows COM / Linux AT-SPI — core pipeline is OS-agnostic |

---

## Quick Start

```bash
./setup.sh   # first time — creates venv, installs deps, prompts for API keys
./run.sh     # start Pair
```

**Required keys:** `SMALLEST_API_KEY` · `ANTHROPIC_API_KEY` · `SLACK_BOT_TOKEN` · `GITHUB_TOKEN`

**macOS permissions needed:** Microphone · Accessibility · Screen Recording (System Settings → Privacy & Security)

---

Built for the CCCL Buildathon · Powered by [Smallest AI](https://smallest.ai) + [Anthropic Claude](https://anthropic.com)
