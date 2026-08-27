#!/usr/bin/env python3
"""
Cross-platform installer for Auto Microsoft Auth.

Usage:
  python3 install.py <chrome-extension-id>
  python3 install.py --set-secret
  python3 install.py --set-secret JBSWY3DPEHPK3PXP
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import stat
import sys
from pathlib import Path

HOST_NAME = "com.autoauth.microsoft"
MANIFEST_FILENAME = f"{HOST_NAME}.json"
CONFIG_DIR = Path.home() / ".auto-auth"
SECRET_FILE = CONFIG_DIR / "secret"

ROOT = Path(__file__).resolve().parent
HOST_SRC = ROOT / "native-host" / "host.py"


def die(msg: str, code: int = 1) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(code)


def normalize_secret(raw: str) -> str:
    return re.sub(r"[^A-Za-z2-7]", "", raw.strip()).upper()


def set_secret(value: str | None) -> None:
    if value is None:
        print("Paste your Microsoft authenticator secret (base32), then press Enter:")
        value = input().strip()
    secret = normalize_secret(value)
    if len(secret) < 8:
        die("That secret looks too short. Copy the full key from Microsoft's setup screen.")
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        CONFIG_DIR.chmod(0o700)
    SECRET_FILE.write_text(secret + "\n", encoding="utf-8")
    if os.name != "nt":
        SECRET_FILE.chmod(0o600)
    print(f"Saved secret to {SECRET_FILE}")


def resolve_python() -> str:
    # Prefer the interpreter running this installer
    return sys.executable


def install_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "auto-auth"
    return Path.home() / ".local" / "share" / "auto-auth"


def write_unix_wrapper(dest_dir: Path, python: str, host_bin: Path) -> Path:
    wrapper = dest_dir / "host-wrapper.sh"
    wrapper.write_text(
        "#!/bin/bash\n"
        f'exec "{python}" "{host_bin}" "$@"\n',
        encoding="utf-8",
    )
    wrapper.chmod(wrapper.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return wrapper


def write_windows_wrapper(dest_dir: Path, python: str, host_bin: Path) -> Path:
    # Chrome on Windows requires the native host path to be a .bat / .cmd / .exe
    wrapper = dest_dir / "host-wrapper.bat"
    # Use pythonw? No — native messaging needs stdin/stdout. python.exe is correct.
    wrapper.write_text(
        "@echo off\r\n"
        f'"{python}" "{host_bin}"\r\n',
        encoding="utf-8",
    )
    return wrapper


def native_messaging_dirs_unix() -> list[Path]:
    home = Path.home()
    system = platform.system()
    dirs: list[Path] = []
    if system == "Darwin":
        support = home / "Library" / "Application Support"
        dirs.extend(
            [
                support / "Google" / "Chrome" / "NativeMessagingHosts",
                support / "Chromium" / "NativeMessagingHosts",
                support / "Google" / "Chrome Canary" / "NativeMessagingHosts",
                support / "Microsoft Edge" / "NativeMessagingHosts",
                support / "BraveSoftware" / "Brave-Browser" / "NativeMessagingHosts",
            ]
        )
    else:
        # Linux / other Unix
        config = home / ".config"
        dirs.extend(
            [
                config / "google-chrome" / "NativeMessagingHosts",
                config / "chromium" / "NativeMessagingHosts",
                config / "microsoft-edge" / "NativeMessagingHosts",
                config / "BraveSoftware" / "Brave-Browser" / "NativeMessagingHosts",
                config / "google-chrome-beta" / "NativeMessagingHosts",
                config / "google-chrome-unstable" / "NativeMessagingHosts",
            ]
        )
    return dirs


def write_manifest(path: Path, host_path: Path, extension_id: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Chrome wants absolute path; on Windows use backslashes escaped in JSON automatically
    payload = {
        "name": HOST_NAME,
        "description": "Auto Microsoft Auth native host",
        "path": str(host_path.resolve()),
        "type": "stdio",
        "allowed_origins": [f"chrome-extension://{extension_id}/"],
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {path}")


def register_windows_registry(manifest_path: Path) -> None:
    try:
        import winreg  # type: ignore
    except ImportError:
        die("winreg is unavailable — run install.py with Windows Python.")

    # HKCU registrations for common Chromium browsers
    keys = [
        rf"Software\Google\Chrome\NativeMessagingHosts\{HOST_NAME}",
        rf"Software\Chromium\NativeMessagingHosts\{HOST_NAME}",
        rf"Software\Microsoft\Edge\NativeMessagingHosts\{HOST_NAME}",
        rf"Software\BraveSoftware\Brave-Browser\NativeMessagingHosts\{HOST_NAME}",
    ]
    manifest = str(manifest_path.resolve())
    for key_path in keys:
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)
        try:
            winreg.SetValueEx(key, None, 0, winreg.REG_SZ, manifest)
        finally:
            winreg.CloseKey(key)
        print(f"Registered HKCU\\{key_path}")


def install_host(extension_id: str) -> None:
    extension_id = extension_id.strip()
    if not re.fullmatch(r"[a-p]{32}", extension_id):
        print(
            "Warning: Chrome extension IDs are usually 32 chars a–p. "
            "Continuing anyway…",
            file=sys.stderr,
        )

    if not HOST_SRC.is_file():
        die(f"Missing host source: {HOST_SRC}")

    python = resolve_python()
    dest = install_dir()
    dest.mkdir(parents=True, exist_ok=True)
    host_bin = dest / "host.py"
    shutil.copy2(HOST_SRC, host_bin)

    if os.name == "nt":
        wrapper = write_windows_wrapper(dest, python, host_bin)
        manifest_path = dest / MANIFEST_FILENAME
        write_manifest(manifest_path, wrapper, extension_id)
        register_windows_registry(manifest_path)
    else:
        wrapper = write_unix_wrapper(dest, python, host_bin)
        for directory in native_messaging_dirs_unix():
            write_manifest(directory / MANIFEST_FILENAME, wrapper, extension_id)

    if not SECRET_FILE.is_file() and not (Path.home() / "microsoft-auth.sh").is_file():
        print(
            f"\nWarning: no secret found at {SECRET_FILE}.\n"
            f"Run:  {python} install.py --set-secret\n",
            file=sys.stderr,
        )
    else:
        print(f"Secret file OK: {SECRET_FILE}" if SECRET_FILE.is_file() else "Using legacy microsoft-auth.sh")

    print(
        "\nInstalled. Fully quit and reopen Chrome, then click "
        '"Test native host" in the extension popup.'
    )


def usage_hint() -> str:
    return """Usage:
  python3 install.py <chrome-extension-id>
  python3 install.py --set-secret [SECRET]

1. Open chrome://extensions
2. Enable Developer mode
3. Load unpacked → select the extension/ folder
4. Copy the extension ID
5. Run: python3 install.py <that-id>
6. Run: python3 install.py --set-secret
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Install Auto Microsoft Auth native messaging host",
        add_help=True,
    )
    parser.add_argument(
        "extension_id",
        nargs="?",
        help="Chrome extension ID from chrome://extensions",
    )
    parser.add_argument(
        "--set-secret",
        nargs="?",
        const="",
        default=None,
        metavar="SECRET",
        help="Save your Microsoft authenticator secret to ~/.auto-auth/secret",
    )
    args = parser.parse_args(argv)

    if args.set_secret is not None:
        set_secret(args.set_secret or None)
        if not args.extension_id:
            return 0

    if not args.extension_id:
        print(usage_hint())
        return 1

    install_host(args.extension_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
