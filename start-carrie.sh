#!/usr/bin/env bash
# Launch Robotron: Ollama, local proxies, web server, and browser.
set -u

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOST="127.0.0.1"
PORT="${ROBOTRON_PORT:-8000}"
URL="http://localhost:${PORT}/avatar.html"
BROWSER_PROFILE="${ROBOTRON_BROWSER_PROFILE:-$HOME/.config/edge-robotron}"

export DISPLAY="${DISPLAY:-:0}"
export XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
export PULSE_RUNTIME_PATH="${PULSE_RUNTIME_PATH:-$XDG_RUNTIME_DIR/pulse}"
export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=/run/user/$(id -u)/bus}"

if [ -f "$APP_DIR/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  . "$APP_DIR/.env"
  set +a
fi

start_detached() {
  local log_file="$1"
  shift
  if command -v setsid >/dev/null 2>&1; then
    setsid -f "$@" >"$log_file" 2>&1
  else
    nohup "$@" >"$log_file" 2>&1 &
  fi
}

# 1) Ollama (the local brain) — start only if not already serving
if ! curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
  echo "Starting Ollama (local brain)..."
  start_detached /tmp/ollama.log env OLLAMA_ORIGINS='*' ollama serve
  for i in $(seq 1 20); do
    curl -s http://localhost:11434/api/tags >/dev/null 2>&1 && break
    sleep 0.5
  done
fi

# 2) Web-search proxy — start only if not already up
if ! curl -s "http://localhost:8765/search?q=ping" >/dev/null 2>&1; then
  echo "Starting web-search proxy on :8765..."
  start_detached /tmp/robotron-search.log python3 "$APP_DIR/search.py"
  sleep 1
fi

# 2b) Local Piper TTS proxy (optional — only if Piper is installed; harmless otherwise)
if ! curl -s "http://localhost:8766/health" >/dev/null 2>&1; then
  start_detached /tmp/robotron-tts.log python3 "$APP_DIR/tts.py"
  sleep 1
fi

# 3) Web server — serve the app on localhost so the mic works
if ! curl -s "$URL" >/dev/null 2>&1; then
  echo "Starting web server on :${PORT}..."
  cd "$APP_DIR" || exit 1
  start_detached /tmp/robotron-http.log python3 -m http.server "$PORT" --bind "$HOST"
  sleep 1
fi

# 4) Open in browser
echo "Robotron is up -> $URL"
OPEN_URL="${URL}?v=$(date +%s)"
EDGE_BIN=""
if command -v microsoft-edge >/dev/null 2>&1; then
  EDGE_BIN="$(command -v microsoft-edge)"
elif command -v microsoft-edge-stable >/dev/null 2>&1; then
  EDGE_BIN="$(command -v microsoft-edge-stable)"
fi

if [ -n "$EDGE_BIN" ]; then
  mkdir -p "$BROWSER_PROFILE"
  start_detached /tmp/robotron-browser.log "$EDGE_BIN" \
    --user-data-dir="$BROWSER_PROFILE" \
    --no-first-run \
    --autoplay-policy=no-user-gesture-required \
    --enable-speech-dispatcher \
    --enable-features=WebSpeechRecognition \
    --new-window \
    "$OPEN_URL"
else
  echo "Microsoft Edge is required for Robotron speech mode, but it was not found." >&2
  echo "Open manually after installing Edge: $OPEN_URL" >&2
  exit 1
fi
