#!/usr/bin/env bash
# Registers the native messaging host so Chrome can run ~/microsoft-auth.sh.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
HOST_SRC="$ROOT/native-host/host.py"
HOST_DIR="$HOME/.local/share/auto-auth"
HOST_BIN="$HOST_DIR/host.py"
MANIFEST_NAME="com.autoauth.microsoft.json"

EXT_ID="${1:-}"

if [[ -z "$EXT_ID" ]]; then
  cat <<'EOF'
Usage: ./install.sh <chrome-extension-id>

1. Open chrome://extensions
2. Enable "Developer mode"
3. Click "Load unpacked" and select the "extension" folder in this repo
4. Copy the extension ID shown under the card
5. Re-run:  ./install.sh <that-id>
EOF
  exit 1
fi

mkdir -p "$HOST_DIR"
cp "$HOST_SRC" "$HOST_BIN"
chmod +x "$HOST_BIN"

# Resolve python3 absolute path for the shebang-less Chrome launch
PYTHON3="$(command -v python3)"
# Chrome launches the host via the "path" field — use a small wrapper so PATH is reliable
WRAPPER="$HOST_DIR/host-wrapper.sh"
cat > "$WRAPPER" <<EOF
#!/bin/bash
exec "$PYTHON3" "$HOST_BIN" "\$@"
EOF
chmod +x "$WRAPPER"

write_manifest() {
  local dest_dir="$1"
  mkdir -p "$dest_dir"
  cat > "$dest_dir/$MANIFEST_NAME" <<EOF
{
  "name": "com.autoauth.microsoft",
  "description": "Runs ~/microsoft-auth.sh and returns the MFA code",
  "path": "$WRAPPER",
  "type": "stdio",
  "allowed_origins": [
    "chrome-extension://$EXT_ID/"
  ]
}
EOF
  echo "Wrote $dest_dir/$MANIFEST_NAME"
}

# Chrome / Chromium / Edge on macOS
write_manifest "$HOME/Library/Application Support/Google/Chrome/NativeMessagingHosts"
write_manifest "$HOME/Library/Application Support/Chromium/NativeMessagingHosts"
write_manifest "$HOME/Library/Application Support/Microsoft Edge/NativeMessagingHosts"
write_manifest "$HOME/Library/Application Support/Google/Chrome Canary/NativeMessagingHosts"

# Verify auth script exists
if [[ ! -x "$HOME/microsoft-auth.sh" ]]; then
  echo "Warning: ~/microsoft-auth.sh is missing or not executable." >&2
fi

echo
echo "Installed. Click \"Test native host\" in the extension popup, or visit a Microsoft MFA prompt."
