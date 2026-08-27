#!/usr/bin/env bash
# Thin wrapper around the cross-platform Python installer.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$ROOT/install.py" "$@"
