# Auto Microsoft Auth

A Chrome extension that automatically fills Microsoft Authenticator **verification codes** when you hit a Microsoft login MFA prompt.

When Microsoft asks you to approve a sign-in (or enter a code), the extension:

1. Detects the MFA screen
2. Clicks **“I can't use my Microsoft Authenticator app right now”** if you're on the push / number-match screen
3. Runs your local `~/microsoft-auth.sh` script to generate a TOTP code
4. Pastes the code and continues sign-in

**Requirements:** macOS, Google Chrome, [Homebrew](https://brew.sh), and Python 3 (usually already installed on Mac).

---

## Overview (what you'll set up)

| Piece | What it is |
| --- | --- |
| `~/microsoft-auth.sh` | A tiny Terminal script that generates your Microsoft 2FA code |
| Chrome extension | Watches Microsoft login pages and pastes the code |
| Native host (`install.sh`) | The bridge that lets Chrome run your script safely |

Do the steps **in order**. Skip nothing the first time.

---

## Part 1 — Generate Microsoft 2FA codes on your Mac (no phone)

### Step 1: Install the code generator

Open **Terminal** (Spotlight → type `Terminal` → Enter) and run:

```bash
brew install oath-toolkit
```

If you don't have Homebrew yet, install it from [https://brew.sh](https://brew.sh), then run the command above again.

---

### Step 2: Get a standard authenticator secret from Microsoft

Microsoft prefers push notifications in their app. You need the **manual secret key** instead.

1. Open your Microsoft security / authenticator setup page in a browser (for work/school accounts this is usually under **Security info** / **Add a sign-in method**).
2. Choose to **add an Authenticator app**.
3. At the bottom of the prompt, click **“I want to use a different authenticator app”**.
4. On the next screen, click **“Can't scan image”** or **“Enter code manually”**.
5. Copy the long secret string (usually 16–32 characters, letters and numbers), e.g. `JBSWY3DPEHPK3PXP`.

Keep this secret private — anyone with it can generate your login codes.

---

### Step 3: Create `~/microsoft-auth.sh`

In Terminal:

```bash
nano ~/microsoft-auth.sh
```

Paste this, replacing `YOUR_SECRET_KEY_HERE` with the secret you copied:

```bash
#!/bin/bash
# Generates the 6-digit Microsoft 2FA token and copies it to your Mac clipboard
oathtool --totp -b "YOUR_SECRET_KEY_HERE" | pbcopy
echo "Microsoft code copied to clipboard!"
```

Save and exit nano:

1. `Ctrl + O`, then `Enter` (save)
2. `Ctrl + X` (exit)

Make it executable:

```bash
chmod +x ~/microsoft-auth.sh
```

---

### Step 4: Test the script by itself

```bash
~/microsoft-auth.sh
```

You should see:

```text
Microsoft code copied to clipboard!
```

Paste somewhere (`Cmd + V`) — you should get a 6-digit code. If that works, continue.

---

## Part 2 — Install this Chrome extension

### Step 5: Get the project on your Mac

If you cloned from GitHub:

```bash
cd "/path/to/auto-auth"
```

(Use the real folder path where you cloned the repo.)

---

### Step 6: Load the extension in Chrome

1. Open Chrome and go to: `chrome://extensions`
2. Turn on **Developer mode** (toggle in the top-right)
3. Click **Load unpacked**
4. Select the **`extension`** folder inside this repo  
   (the folder that contains `manifest.json` — not the repo root)
5. Confirm **Auto Microsoft Auth** appears in your extensions list
6. **Copy the Extension ID** shown under the extension card  
   (a long string like `abcdefghijklmnopqrstuvwxyzabcdef`)

Leave that ID on your clipboard / sticky note — you need it next.

---

### Step 7: Connect Chrome to your auth script

Still in Terminal, from the repo root:

```bash
chmod +x install.sh
./install.sh YOUR_EXTENSION_ID_HERE
```

Example:

```bash
./install.sh abcdefghijklmnopqrstuvwxyzabcdef
```

This registers a small native messaging host so Chrome can run `~/microsoft-auth.sh`.

---

### Step 8: Verify the bridge works

1. In Chrome, click the **Auto Microsoft Auth** extension icon
2. Click **Test native host**
3. You should see something like: `OK — got code 123456`

If you see an error, jump to [Troubleshooting](#troubleshooting).

---

## Part 3 — Use it

Sign in to any site that uses Microsoft login. When MFA appears:

- On the **Approve sign-in / number match** screen, the extension clicks **“I can't use my Microsoft Authenticator app right now”**
- On the **Enter code** screen, it fills the code and continues

You usually don't need to open Terminal anymore.

---

## Troubleshooting

### `Test native host` fails / “Specified native messaging host not found”

- Re-run `./install.sh YOUR_EXTENSION_ID` with the **current** extension ID from `chrome://extensions`
- If you removed and re-loaded the extension, the ID may have changed — run `install.sh` again
- Fully quit Chrome (`Cmd + Q`) and reopen it after installing

### “oathtool: command not found” or empty / invalid code

- Confirm Homebrew installed the tool: `brew install oath-toolkit`
- Confirm the script works alone: `~/microsoft-auth.sh`
- Confirm the secret in `~/microsoft-auth.sh` is correct (no spaces, quotes around it)

### Extension doesn't click / fill on the login page

1. Reload the extension on `chrome://extensions` (circular refresh button)
2. Refresh the Microsoft login tab
3. Confirm you're on a `login.microsoftonline.com` (or similar Microsoft login) page
4. Open DevTools → Console and look for `[Auto Microsoft Auth]` messages

### After updating this repo

```bash
./install.sh YOUR_EXTENSION_ID
```

Then click the refresh button on the extension card in `chrome://extensions`.

---

## Security notes

- Your TOTP secret lives only in `~/microsoft-auth.sh` — **do not commit that file to GitHub**
- This extension only runs on Microsoft login hosts and only talks to the local native host you install
- Treat `~/microsoft-auth.sh` like a password backup

---

## Uninstall

1. Remove the extension from `chrome://extensions`
2. Optional cleanup:

```bash
rm -rf ~/.local/share/auto-auth
rm -f ~/Library/Application\ Support/Google/Chrome/NativeMessagingHosts/com.autoauth.microsoft.json
rm -f ~/microsoft-auth.sh
```
