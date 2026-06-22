#!/usr/bin/env bash
# Launch Robotron: Ollama, local proxies, web server, and browser.
set -u

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOST="127.0.0.1"
PORT="${ROBOTRON_PORT:-8000}"
URL="http://localhost:${PORT}/avatar.html"

# 1) Ollama (the local brain) — start only if not already serving
if ! curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
  echo "Starting Ollama (local brain)..."
  OLLAMA_ORIGINS=* nohup ollama serve >/tmp/ollama.log 2>&1 &
  for i in $(seq 1 20); do
    curl -s http://localhost:11434/api/tags >/dev/null 2>&1 && break
    sleep 0.5
  done
fi

# 2) Web-search proxy — start only if not already up
if ! curl -s "http://localhost:8765/search?q=ping" >/dev/null 2>&1; then
  echo "Starting web-search proxy on :8765..."
  nohup python3 "$APP_DIR/search.py" >/tmp/robotron-search.log 2>&1 &
  sleep 1
fi

# 2b) Local Piper TTS proxy (optional — only if Piper is installed; harmless otherwise)
if ! curl -s "http://localhost:8766/health" >/dev/null 2>&1; then
  nohup python3 "$APP_DIR/tts.py" >/tmp/robotron-tts.log 2>&1 &
  sleep 1
fi

# 3) Web server — serve the app on localhost so the mic works
if ! curl -s "$URL" >/dev/null 2>&1; then
  echo "Starting web server on :${PORT}..."
  cd "$APP_DIR" || exit 1
  nohup python3 -m http.server "$PORT" --bind "$HOST" >/tmp/robotron-http.log 2>&1 &
  sleep 1
fi

# 4) Open in browser
echo "Robotron is up -> $URL"
( xdg-open "$URL" >/dev/null 2>&1 || google-chrome "$URL" >/dev/null 2>&1 ) &
