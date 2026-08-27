#!/usr/bin/env python3
"""Native messaging host: runs ~/microsoft-auth.sh and returns the MFA code."""

from __future__ import annotations

import json
import os
import stat
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

AUTH_SCRIPT = Path.home() / "microsoft-auth.sh"

# Chrome launches native hosts with a tiny PATH that omits Homebrew.
EXTRA_PATH = "/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/local/sbin"


def read_message() -> dict | None:
    raw_len = sys.stdin.buffer.read(4)
    if len(raw_len) == 0:
        return None
    msg_len = struct.unpack("<I", raw_len)[0]
    data = sys.stdin.buffer.read(msg_len)
    return json.loads(data.decode("utf-8"))


def send_message(payload: dict) -> None:
    encoded = json.dumps(payload).encode("utf-8")
    sys.stdout.buffer.write(struct.pack("<I", len(encoded)))
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.flush()


def host_env(extra_bin: Path | None = None) -> dict[str, str]:
    env = os.environ.copy()
    parts = [EXTRA_PATH, env.get("PATH", "/usr/bin:/bin:/usr/sbin:/sbin")]
    if extra_bin is not None:
        parts.insert(0, str(extra_bin))
    env["PATH"] = ":".join(parts)
    return env


def digits_only(text: str) -> str:
    return "".join(ch for ch in text.strip() if ch.isdigit())


def generate_code() -> str:
    if not AUTH_SCRIPT.is_file():
        raise FileNotFoundError(f"Missing auth script: {AUTH_SCRIPT}")
    if not os.access(AUTH_SCRIPT, os.X_OK):
        raise PermissionError(f"Auth script is not executable: {AUTH_SCRIPT}")

    with tempfile.TemporaryDirectory(prefix="auto-auth-") as tmp:
        tmp_path = Path(tmp)
        # Intercept pbcopy so we get the code even if the pasteboard is unavailable
        # under Chrome's launch environment.
        capture_file = tmp_path / "code.txt"
        fake_pbcopy = tmp_path / "pbcopy"
        fake_pbcopy.write_text(
            "#!/bin/bash\n"
            f'cat > "{capture_file}"\n'
            # Also try the real clipboard for the user's other tools
            f'/usr/bin/pbcopy < "{capture_file}" 2>/dev/null || true\n'
        )
        fake_pbcopy.chmod(fake_pbcopy.stat().st_mode | stat.S_IXUSR)

        result = subprocess.run(
            ["/bin/bash", str(AUTH_SCRIPT)],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
            env=host_env(tmp_path),
        )

        captured = capture_file.read_text() if capture_file.is_file() else ""
        code = digits_only(captured)

        if not code:
            paste = subprocess.run(
                ["/usr/bin/pbpaste"],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
                env=host_env(),
            )
            code = digits_only(paste.stdout or "")

        if len(code) < 6:
            err = (result.stderr or result.stdout or "").strip()
            detail = err or f"clipboard={captured!r}"
            raise RuntimeError(
                f"No valid MFA code from microsoft-auth.sh ({detail}). "
                "Is oathtool installed and on PATH?"
            )
        return code[:8]


def main() -> int:
    message = read_message()
    if message is None:
        return 0

    action = message.get("action", "generate")
    if action != "generate":
        send_message({"ok": False, "error": f"Unknown action: {action}"})
        return 0

    try:
        code = generate_code()
        send_message({"ok": True, "code": code})
    except Exception as exc:  # noqa: BLE001 — surface any host failure to the extension
        send_message({"ok": False, "error": str(exc)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
