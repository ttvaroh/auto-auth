#!/usr/bin/env python3
"""
Optional manual helper: print (and copy) the current Microsoft MFA code.

Reads ~/.auto-auth/secret — same file the Chrome native host uses.
Works on macOS, Windows, and Linux.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

# Reuse TOTP logic from the native host when available
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "native-host"))

from host import (  # noqa: E402
    SECRET_FILE,
    generate_code,
    read_secret_file,
    secret_from_legacy_sh,
)


def copy_to_clipboard(text: str) -> bool:
    if sys.platform == "darwin":
        proc = subprocess.run(["pbcopy"], input=text.encode(), check=False)
        return proc.returncode == 0
    if os_name_is_windows():
        proc = subprocess.run(["clip"], input=text, text=True, check=False)
        return proc.returncode == 0
    for cmd in (
        ["wl-copy"],
        ["xclip", "-selection", "clipboard"],
        ["xsel", "--clipboard", "--input"],
    ):
        if shutil.which(cmd[0]):
            proc = subprocess.run(cmd, input=text.encode(), check=False)
            if proc.returncode == 0:
                return True
    return False


def os_name_is_windows() -> bool:
    return sys.platform.startswith("win")


def main() -> int:
    if not read_secret_file() and not secret_from_legacy_sh():
        print(
            f"No secret found. Run:\n  python3 install.py --set-secret\n"
            f"(expected file: {SECRET_FILE})",
            file=sys.stderr,
        )
        return 1

    code = generate_code()
    copied = copy_to_clipboard(code)
    if copied:
        print(f"Microsoft code copied to clipboard: {code}")
    else:
        print(code)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
