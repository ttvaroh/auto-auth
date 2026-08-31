# Auto Microsoft Auth

A Chrome extension that automatically fills Microsoft Authenticator **verification codes** when you hit a Microsoft login MFA prompt.

Works on **macOS**, **Windows**, and **Linux**.

When Microsoft asks you to approve a sign-in (or enter a code), the extension:

1. Detects the MFA screen
2. Clicks **“I can't use my Microsoft Authenticator app right now”** if you're on the push / number-match screen
3. Generates a TOTP code locally (via a native messaging host)
4. Pastes the code and continues sign-in

---

## Platform support

| Platform | Supported? | Installer |
| --- | --- | --- |
| **macOS** | Yes | `./install.sh` or `python3 install.py` |
| **Windows** | Yes | `.\install.ps1` or `python install.py` |
| **Linux** | Yes | `./install.sh` or `python3 install.py` |

**Requirements (all platforms):** Google Chrome (or Chromium / Edge / Brave) and **Python 3**.

---

## How secrets work (all platforms)

The extension never stores your secret. The native host reads it from:

```text
~/.auto-auth/secret
```

On Windows that is usually:

```text
C:\Users\<you>\.auto-auth\secret
```

The file should contain only your Microsoft authenticator base32 secret (one line).

**Legacy (macOS):** if you already have `~/microsoft-auth.sh` with an `oathtool --totp -b "SECRET"` line, the host can still use that. New installs should use `~/.auto-auth/secret`.

---

## Shared Step A — Get your Microsoft authenticator secret

Microsoft prefers push notifications. You need the **manual secret key** instead.

1. Open [account.microsoft.com/security](account.microsoft.com/security) and navigate **My Account** → **Security Info** → **Add a sign-in method**.
2. Choose to **add an Authenticator app**.
3. Click **“I want to use a different authenticator app”**.
4. Click **“Can't scan image”** or **“Enter code manually”**.
5. Copy the long secret string (usually 16–32 characters), e.g. `JBSWY3DPEHPK3PXP`.

Keep this private — anyone with it can generate your login codes.

---

## Shared Step B — Load the Chrome extension

1. Clone or download this repo
2. Open Chrome → `chrome://extensions`
3. Turn on **Developer mode** (top-right)
4. Click **Load unpacked**
5. Select the **`extension`** folder (the one with `manifest.json`, not the repo root)
6. Copy the **Extension ID** under the card (32 characters)

---

## macOS setup

### 1. Save your secret

```bash
cd /path/to/auto-auth
python3 install.py --set-secret
```

Paste the secret when prompted (or pass it: `python3 install.py --set-secret YOUR_SECRET`).

### 2. Connect Chrome to the native host
get the extension id from the chrome extension in `chrome://extensions` and run the following:

```bash
chmod +x install.sh
./install.sh YOUR_EXTENSION_ID
```

### 3. Verify

1. Fully quit Chrome (`Cmd + Q`) and reopen it  
2. Click the extension icon → **Test native host**  
3. You should see `OK — got code 123456`

### Optional: generate a code in Terminal

```bash
python3 scripts/microsoft-auth.py
```

### Optional legacy script (`oathtool` + clipboard)

Only needed if you prefer the old workflow:

```bash
brew install oath-toolkit
nano ~/microsoft-auth.sh
```

```bash
#!/bin/bash
oathtool --totp -b "YOUR_SECRET_KEY_HERE" | pbcopy
echo "Microsoft code copied to clipboard!"
```

```bash
chmod +x ~/microsoft-auth.sh
```

---

## Windows setup

### 1. Install Python 3

Install from [python.org](https://www.python.org/downloads/) and check **“Add python.exe to PATH”**.

Confirm in **PowerShell** or **Command Prompt**:

```powershell
python --version
```

### 2. Save your secret

In PowerShell, from the repo folder:

```powershell
cd C:\path\to\auto-auth
python install.py --set-secret
```

Paste the secret when prompted.

### 3. Connect Chrome to the native host

```powershell
.\install.ps1 YOUR_EXTENSION_ID
```

If PowerShell blocks scripts:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Or call Python directly:

```powershell
python install.py YOUR_EXTENSION_ID
```

### 4. Verify

1. Fully quit Chrome (tray icon → Exit) and reopen it  
2. Click the extension icon → **Test native host**  
3. You should see `OK — got code 123456`

### Optional: generate a code in a terminal

```powershell
python scripts\microsoft-auth.py
```

---

## Linux setup

### 1. Install Python 3

```bash
# Debian/Ubuntu
sudo apt update && sudo apt install -y python3

# Fedora
sudo dnf install -y python3
```

### 2. Save your secret

```bash
cd /path/to/auto-auth
python3 install.py --set-secret
```

### 3. Connect Chrome to the native host

```bash
chmod +x install.sh
./install.sh YOUR_EXTENSION_ID
```

This writes native-messaging manifests under `~/.config/google-chrome/`, `~/.config/chromium/`, `~/.config/microsoft-edge/`, and Brave paths when present.

### 4. Verify

1. Fully quit the browser and reopen it  
2. Click the extension icon → **Test native host**  
3. You should see `OK — got code 123456`

### Optional: generate a code in a terminal

```bash
python3 scripts/microsoft-auth.py
```

Clipboard copy on Linux uses `wl-copy`, `xclip`, or `xsel` when available; otherwise the code is printed.

---

## Using it

Sign in to any site that uses Microsoft login. When MFA appears:

- On the **Approve sign-in / number match** screen, the extension clicks **“I can't use my Microsoft Authenticator app right now”**
- Then it selects code entry if needed, fills the code, and continues

You usually do not need to open a terminal after setup.

---

## Troubleshooting

### “Specified native messaging host not found”

- Re-run the installer with the **current** extension ID from `chrome://extensions` (IDs change if you remove/reload unpacked)
- Fully quit and reopen the browser after installing
- **Windows:** confirm `python install.py YOUR_ID` completed without errors (it writes a registry key under `HKCU\Software\Google\Chrome\NativeMessagingHosts\`)

### “No secret found” / invalid code

```bash
python3 install.py --set-secret
```

Confirm the file exists and contains only the base32 secret:

- macOS / Linux: `~/.auto-auth/secret`
- Windows: `%USERPROFILE%\.auto-auth\secret`

### Extension doesn't click / fill

1. Reload the extension on `chrome://extensions`
2. Refresh the Microsoft login tab
3. Confirm the URL is a Microsoft login host (`login.microsoftonline.com`, etc.)
4. Open DevTools → Console for `[Auto Microsoft Auth]` messages

### After updating this repo

Re-run the installer with your extension ID, then click the refresh button on the extension card.

---

## Security notes

- Your TOTP secret lives in `~/.auto-auth/secret` (or a legacy home-directory script) — **never commit it to GitHub**
- The extension only runs on Microsoft login hosts and only talks to the local native host you install
- Treat the secret file like a password backup (`chmod 600` is applied automatically on macOS/Linux)

---

## Uninstall

1. Remove the extension from `chrome://extensions`

**macOS / Linux:**

```bash
rm -rf ~/.local/share/auto-auth ~/.auto-auth
rm -f ~/.config/google-chrome/NativeMessagingHosts/com.autoauth.microsoft.json
rm -f ~/Library/Application\ Support/Google/Chrome/NativeMessagingHosts/com.autoauth.microsoft.json
```

**Windows (PowerShell):**

```powershell
Remove-Item -Recurse -Force "$env:LOCALAPPDATA\auto-auth" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "$env:USERPROFILE\.auto-auth" -ErrorAction SilentlyContinue
Remove-Item -Path "HKCU:\Software\Google\Chrome\NativeMessagingHosts\com.autoauth.microsoft" -ErrorAction SilentlyContinue
```
