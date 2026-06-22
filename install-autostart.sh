#!/usr/bin/env bash
# Install a user-level autostart entry for Robotron.
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AUTOSTART_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/autostart"
TARGET="$AUTOSTART_DIR/robotron.desktop"

mkdir -p "$AUTOSTART_DIR"
sed "s#^Exec=.*#Exec=$APP_DIR/start-carrie.sh#" "$APP_DIR/robotron.desktop" > "$TARGET"
chmod +x "$APP_DIR/start-carrie.sh"

echo "Installed $TARGET"
