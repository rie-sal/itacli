"""Install a one-word `itacli` launcher on PATH, so the app starts by typing
`itacli` (like `claude`). Points at THIS checkout's venv + a default data dir.
"""
import os
import sys

BIN_DIR = os.path.expanduser("~/.local/bin")
MARK = "# added by itacli"


def _project_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _shell_profiles():
    home = os.path.expanduser("~")
    return [os.path.join(home, ".zshrc"), os.path.join(home, ".bash_profile")]


def _ensure_on_path():
    """Make sure ~/.local/bin is on PATH (append to shell profiles if missing).
    Returns True if it was already on PATH."""
    if BIN_DIR in os.environ.get("PATH", "").split(":"):
        return True
    line = '%s\nexport PATH="$HOME/.local/bin:$PATH"\n' % MARK
    for profile in _shell_profiles():
        try:
            existing = ""
            if os.path.exists(profile):
                with open(profile, encoding="utf-8") as f:
                    existing = f.read()
            if MARK not in existing:
                with open(profile, "a", encoding="utf-8") as f:
                    f.write("\n" + line)
        except OSError:
            pass
    return False


def install_launcher():
    """Create ~/.local/bin/itacli. Returns (path, already_on_path)."""
    os.makedirs(BIN_DIR, exist_ok=True)
    launcher = os.path.join(BIN_DIR, "itacli")
    # No forced data dir: use profiles (~/Library/Application Support/itacli).
    # ITACLI_DATA_DIR still overrides if the user exports it (for sandboxing).
    body = (
        "#!/bin/bash\n"
        'exec "%s" "%s" "$@"\n' % (sys.executable, os.path.join(_project_root(), "run.py"))
    )
    with open(launcher, "w", encoding="utf-8") as f:
        f.write(body)
    os.chmod(launcher, 0o755)
    on_path = _ensure_on_path()
    return launcher, on_path
