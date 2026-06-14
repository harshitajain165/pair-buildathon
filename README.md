# Pair

A voice-first AI developer assistant for macOS. Speak naturally — Pair executes real developer actions.

**Stack:** Smallest AI Pulse (STT) → Claude (intelligence + tool calling) → Smallest AI Lightning (TTS)

---

## What it can do

- **Open apps, URLs, folders** — "Open GitHub" / "Open my Desktop"
- **Edit code** — "Add error handling to auth.py"
- **Run shell commands** — "Run the tests" / "Git status"
- **Review changes** — "Review my uncommitted changes"
- **Send Slack messages** — "Message Harshita: shipping in 10"
- **GitHub** — create issues, list open PRs
- **Standup** — generate from git history, post to Slack
- **Spotify** — play, pause, next, search
- **Modify UI** — "Make the background dark" (takes screenshot → edits CSS)
- **Repo summary** — "What does this codebase do?"
- **Catch me up** — "What was I last working on?"
- **Screen analysis** — "What's wrong with this?" (Claude vision)

---

## Setup

```bash
git clone https://github.com/harshitajain165/pair-buildathon
cd pair-buildathon
./setup.sh
```

`setup.sh` creates the virtual environment, installs all dependencies, and walks you through entering your API keys interactively.

### API keys needed

| Key | Where to get it | Required |
|-----|----------------|----------|
| `SMALLEST_API_KEY` | waves.smallest.ai | ✅ |
| `ANTHROPIC_API_KEY` | console.anthropic.com | ✅ |
| `SLACK_BOT_TOKEN` | api.slack.com/apps | Optional |
| `GITHUB_TOKEN` | github.com/settings/tokens | Optional |

### macOS permissions

Go to **System Settings → Privacy & Security** and grant Terminal access to:
- **Microphone**
- **Accessibility**
- **Screen Recording**

---

## Run

```bash
./run.sh
```

Then just talk.
