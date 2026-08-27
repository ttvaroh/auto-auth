#!/usr/bin/env python3
"""
Native messaging host for Auto Microsoft Auth (macOS / Windows / Linux).

Priority for generating a code:
1. TOTP from ~/.auto-auth/secret (or %USERPROFILE%\\.auto-auth\\secret)
2. TOTP secret parsed from ~/microsoft-auth.sh (macOS legacy)
3. External auth script if present (microsoft-auth.sh / .ps1 / .py / .cmd)
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HOST_NAME = "com.autoauth.microsoft"
CONFIG_DIR = Path.home() / ".auto-auth"
SECRET_FILE = CONFIG_DIR / "secret"
LEGACY_SH = Path.home() / "microsoft-auth.sh"
LEGACY_PS1 = Path.home() / "microsoft-auth.ps1"
LEGACY_PY = Path.home() / "microsoft-auth.py"
LEGACY_CMD = Path.home() / "microsoft-auth.cmd"

# Chrome launches native hosts with a tiny PATH.
EXTRA_PATH_UNIX = "/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/local/sbin:/usr/bin:/bin"


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


def digits_only(text: str) -> str:
    return "".join(ch for ch in text.strip() if ch.isdigit())


def normalize_secret(raw: str) -> str:
    # Allow spaces/dashes people sometimes copy from Microsoft UI
    return re.sub(r"[^A-Za-z2-7]", "", raw.strip()).upper()


def totp(secret_b32: str, digits: int = 6, period: int = 30) -> str:
    secret = normalize_secret(secret_b32)
    if len(secret) < 8:
        raise ValueError("TOTP secret looks too short")
    padding = "=" * ((8 - len(secret) % 8) % 8)
    key = base64.b32decode(secret + padding, casefold=True)
    counter = int(time.time() // period)
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return f"{code % (10 ** digits):0{digits}d}"


def read_secret_file() -> str | None:
    if not SECRET_FILE.is_file():
        return None
    text = SECRET_FILE.read_text(encoding="utf-8").strip()
    if not text:
        return None
    # Allow either plain secret or JSON {"secret":"..."}
    if text.startswith("{"):
        data = json.loads(text)
        value = data.get("secret")
        return str(value).strip() if value else None
    # First non-empty, non-comment line
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            return line
    return None


def secret_from_legacy_sh() -> str | None:
    if not LEGACY_SH.is_file():
        return None
    text = LEGACY_SH.read_text(encoding="utf-8", errors="ignore")
    match = re.search(r"""oathtool\s+--totp\s+-b\s+["']([A-Za-z0-9=]+)["']""", text)
    return match.group(1) if match else None


def host_env(extra_bin: Path | None = None) -> dict[str, str]:
    env = os.environ.copy()
    if os.name == "nt":
        extras = [
            str(Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Python"),
            r"C:\Windows\System32",
        ]
        path = env.get("PATH", "")
        if extra_bin is not None:
            path = str(extra_bin) + os.pathsep + path
        env["PATH"] = os.pathsep.join([p for p in extras if p]) + os.pathsep + path
        return env

    parts = [EXTRA_PATH_UNIX, env.get("PATH", "/usr/bin:/bin")]
    if extra_bin is not None:
        parts.insert(0, str(extra_bin))
    env["PATH"] = ":".join(parts)
    return env


def run_and_capture_code(command: list[str], env: dict[str, str] | None = None) -> str:
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
        env=env or host_env(),
        shell=False,
    )
    # Prefer digits from stdout; scripts may also print a status line
    for candidate in (result.stdout or "", result.stderr or ""):
        code = digits_only(candidate)
        if len(code) >= 6:
            return code[:8]
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "unknown error").strip()
        raise RuntimeError(f"Auth command failed: {err}")
    raise RuntimeError("Auth command produced no MFA code")


def code_from_shell_script(script: Path) -> str:
    """Run a bash script that pipes to pbcopy; intercept clipboard helpers."""
    with tempfile.TemporaryDirectory(prefix="auto-auth-") as tmp:
        tmp_path = Path(tmp)
        capture_file = tmp_path / "code.txt"

        fake_pbcopy = tmp_path / "pbcopy"
        fake_pbcopy.write_text(
            "#!/bin/sh\n"
            f'cat > "{capture_file}"\n'
            f'(command -v pbcopy >/dev/null && /usr/bin/pbcopy < "{capture_file}") 2>/dev/null || true\n'
            f'(command -v xclip >/dev/null && xclip -selection clipboard < "{capture_file}") 2>/dev/null || true\n'
            f'(command -v wl-copy >/dev/null && wl-copy < "{capture_file}") 2>/dev/null || true\n',
            encoding="utf-8",
        )
        fake_pbcopy.chmod(0o755)

        bash = shutil.which("bash") or "/bin/bash"
        result = subprocess.run(
            [bash, str(script)],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
            env=host_env(tmp_path),
        )

        captured = capture_file.read_text(encoding="utf-8") if capture_file.is_file() else ""
        code = digits_only(captured) or digits_only(result.stdout or "")
        if len(code) >= 6:
            return code[:8]

        err = (result.stderr or result.stdout or "").strip()
        detail = err or f"capture={captured!r}"
        raise RuntimeError(f"No valid MFA code from {script.name} ({detail})")


def code_from_ps1(script: Path) -> str:
    powershell = shutil.which("powershell") or shutil.which("pwsh")
    if not powershell:
        raise RuntimeError("PowerShell not found to run microsoft-auth.ps1")
    return run_and_capture_code(
        [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)]
    )


def code_from_python_script(script: Path) -> str:
    return run_and_capture_code([sys.executable, str(script)])


def code_from_cmd(script: Path) -> str:
    # cmd.exe scripts: run via shell so .cmd works
    result = subprocess.run(
        str(script),
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
        env=host_env(),
        shell=True,
    )
    code = digits_only(result.stdout or "")
    if len(code) >= 6:
        return code[:8]
    err = (result.stderr or result.stdout or "").strip()
    raise RuntimeError(f"No valid MFA code from {script.name} ({err})")


def generate_code() -> str:
    secret = read_secret_file() or secret_from_legacy_sh()
    if secret:
        return totp(secret)

    errors: list[str] = []

    if LEGACY_SH.is_file():
        try:
            return code_from_shell_script(LEGACY_SH)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{LEGACY_SH.name}: {exc}")

    if LEGACY_PS1.is_file():
        try:
            return code_from_ps1(LEGACY_PS1)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{LEGACY_PS1.name}: {exc}")

    if LEGACY_PY.is_file():
        try:
            return code_from_python_script(LEGACY_PY)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{LEGACY_PY.name}: {exc}")

    if LEGACY_CMD.is_file():
        try:
            return code_from_cmd(LEGACY_CMD)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{LEGACY_CMD.name}: {exc}")

    hint = (
        f"Create {SECRET_FILE} containing your base32 Microsoft authenticator secret, "
        "or place microsoft-auth.sh / microsoft-auth.ps1 / microsoft-auth.py in your home directory."
    )
    if errors:
        raise RuntimeError(hint + " Attempts: " + " | ".join(errors))
    raise FileNotFoundError(hint)


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
    except Exception as exc:  # noqa: BLE001
        send_message({"ok": False, "error": str(exc)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
