# Installing itacli (as a fresh user)

itacli is a Python app. Your **code** and your **data** are separate:
- code lives wherever you clone it (has its own `.venv`);
- data (DB + cached texts) lives at `~/Library/Application Support/itacli` by
  default, or wherever `ITACLI_DATA_DIR` points.

So to test as a brand-new user without touching a development copy, put the
code in a new folder **and** point it at a fresh data dir.

## Easiest: one command

Paste into Terminal — clones and installs everything, then tells you how to run:

```bash
curl -fsSL https://raw.githubusercontent.com/rie-sal/itacli/main/bootstrap.sh | bash
```

## Easiest without typing: double-click

Download **`itacli-install.command`** from the repo and double-click it in
Finder. The first time, macOS Gatekeeper may block it — right-click the file →
**Open** → **Open** to confirm you trust it. It installs to `~/itacli`.

The manual steps below are the same thing, spelled out.

## 1. Get the code

```bash
git clone https://github.com/rie-sal/itacli.git ~/itacli
cd ~/itacli
```

## 2. Install (one command)

```bash
./install.sh
```

This creates an isolated `.venv` and installs spaCy (+ the Italian model) and
mlconjug3. Nothing touches your system Python.

## 3. Run

```bash
# fresh, isolated data dir so it behaves like a first-time user:
ITACLI_DATA_DIR="$HOME/itacli-data" .venv/bin/python run.py
```

First launch walks you through: your name, the capture hotkey, the offline
translation language pack, and the one-time macOS setup.

## What still needs a one-time macOS setup

These are machine-level (shared across any copy on the same Mac), and the app
walks you through them (`run.py setup`, or during onboarding):
- **Accessibility** permission (to copy the selection in any app),
- the **capture hotkey** (Automator Quick Action + a Services shortcut),
- the **"itacli Translate" Shortcut** (Apple on-device translation),
- the **Italian language pack** (so translation works offline),
- **Anki** open with the **AnkiConnect** add-on, for cards to sync.

## Fully clean uninstall of a test run

```bash
rm -rf ~/itacli ~/itacli-data
```
(Plus remove the Quick Action / Shortcut / hotkey if you created them.)
