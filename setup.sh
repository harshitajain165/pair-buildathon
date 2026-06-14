#!/bin/bash
set -e

echo ""
echo "  ██████╗  █████╗ ██╗██████╗ "
echo "  ██╔══██╗██╔══██╗██║██╔══██╗"
echo "  ██████╔╝███████║██║██████╔╝"
echo "  ██╔═══╝ ██╔══██║██║██╔══██╗"
echo "  ██║     ██║  ██║██║██║  ██║"
echo "  ╚═╝     ╚═╝  ╚═╝╚═╝╚═╝  ╚═╝"
echo ""
echo "  Voice AI developer assistant"
echo "  ─────────────────────────────────────────"
echo ""

# ── Python check ─────────────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
  echo "  ✗  Python 3 not found. Install it from python.org"
  exit 1
fi

PY_VER=$(python3 -c "import sys; print(sys.version_info.major * 10 + sys.version_info.minor)")
if [ "$PY_VER" -lt 39 ]; then
  echo "  ✗  Python 3.9+ required. You have $(python3 --version)"
  exit 1
fi

echo "  ✓  Python $(python3 --version | awk '{print $2}')"

# ── Virtualenv ────────────────────────────────────────────────────────────────
if [ ! -d ".venv" ]; then
  echo "  →  Creating virtual environment..."
  python3 -m venv .venv
fi

source .venv/bin/activate
echo "  ✓  Virtual environment ready"

# ── Dependencies ──────────────────────────────────────────────────────────────
echo "  →  Installing dependencies (this may take a minute)..."
pip install -q -r requirements.txt
echo "  ✓  Dependencies installed"

# ── API keys ─────────────────────────────────────────────────────────────────
echo ""
echo "  ─────────────────────────────────────────"
echo "  API Key Setup"
echo "  ─────────────────────────────────────────"
echo ""

# Load existing .env if present so we can show current values
if [ -f ".env" ]; then
  source .env 2>/dev/null || true
fi

prompt_key() {
  local name=$1
  local description=$2
  local where=$3
  local current=$4

  echo "  $description"
  echo "  Get it at: $where"
  if [ -n "$current" ]; then
    echo -n "  $name [keep current: ${current:0:12}...]: "
  else
    echo -n "  $name: "
  fi
  read -r value
  if [ -z "$value" ] && [ -n "$current" ]; then
    value=$current
  fi
  echo "$value"
}

echo "  Required keys"
echo ""

SMALLEST=$(prompt_key "SMALLEST_API_KEY" "Smallest AI — for voice (STT + TTS)" "waves.smallest.ai" "$SMALLEST_API_KEY")
echo ""
ANTHROPIC=$(prompt_key "ANTHROPIC_API_KEY" "Anthropic — for Claude intelligence + tool calling" "console.anthropic.com" "$ANTHROPIC_API_KEY")

echo ""
echo "  Optional keys (press Enter to skip)"
echo ""

SLACK=$(prompt_key "SLACK_BOT_TOKEN" "Slack — send messages, post standups" "api.slack.com/apps" "$SLACK_BOT_TOKEN")
echo ""
GITHUB=$(prompt_key "GITHUB_TOKEN" "GitHub — create issues, list PRs" "github.com/settings/tokens" "$GITHUB_TOKEN")

# Write .env
cat > .env <<EOF
SMALLEST_API_KEY=$SMALLEST
ANTHROPIC_API_KEY=$ANTHROPIC
SLACK_BOT_TOKEN=$SLACK
GITHUB_TOKEN=$GITHUB
EOF

echo ""
echo "  ✓  API keys saved to .env"

# ── macOS permissions ─────────────────────────────────────────────────────────
echo ""
echo "  ─────────────────────────────────────────"
echo "  macOS Permissions Required"
echo "  ─────────────────────────────────────────"
echo ""
echo "  Open System Settings → Privacy & Security and grant:"
echo ""
echo "    🎤  Microphone      → Terminal (or your IDE)"
echo "    ♿  Accessibility   → Terminal"
echo "    🖥️   Screen Recording → Terminal"
echo ""
echo "  Then re-run this terminal after granting permissions."
echo ""

# ── Done ──────────────────────────────────────────────────────────────────────
echo "  ─────────────────────────────────────────"
echo "  Setup complete. To start Pair:"
echo ""
echo "    ./run.sh"
echo ""
echo "  ─────────────────────────────────────────"
echo ""
