"""Best-effort automatic AnkiConnect install (SPECS §7-vocab).

Drops the AnkiConnect add-on straight into Anki's add-ons folder so the user
never has to type the 2055492159 code. Anki must have run at least once (so the
Anki2 folder exists) and must be RESTARTED afterwards. Falls back to the manual
route if the download or folder isn't available.
"""
import json
import os
import urllib.error
import urllib.request

# AnkiConnect (add-on 2055492159) - single-file add-on; fetch its source.
RAW_URLS = [
    "https://raw.githubusercontent.com/FooSoft/anki-connect/master/plugin/__init__.py",
    "https://raw.githubusercontent.com/FooSoft/anki-connect/main/plugin/__init__.py",
]

DEFAULT_CONFIG = {
    "apiKey": None,
    "apiLogPath": None,
    "ignoreOriginList": [],
    "webBindAddress": "127.0.0.1",
    "webBindPort": 8765,
    "webCorsOrigin": "http://localhost",
    "webCorsOriginList": ["http://localhost"],
}


def anki2_dir():
    # macOS location; other platforms handled when we port.
    return os.path.join(os.path.expanduser("~"), "Library", "Application Support", "Anki2")


def _download():
    for url in RAW_URLS:
        try:
            with urllib.request.urlopen(url, timeout=20) as resp:
                data = resp.read()
        except (urllib.error.URLError, OSError):
            continue
        if len(data) > 5000 and (b"webBindPort" in data or b"AnkiConnect" in data):
            return data
    return None


def install_ankiconnect(base=None):
    """Install AnkiConnect. Returns (ok, message)."""
    base = base or anki2_dir()
    if not os.path.isdir(base):
        return False, ("Anki hasn't run yet (no Anki2 folder). Open Anki once, "
                       "then try again.")
    code = _download()
    if not code:
        return False, ("Couldn't download AnkiConnect - add it manually in Anki "
                       "(Tools > Add-ons > Get Add-ons > code 2055492159).")
    dest = os.path.join(base, "addons21", "2055492159")
    try:
        os.makedirs(dest, exist_ok=True)
        with open(os.path.join(dest, "__init__.py"), "wb") as f:
            f.write(code)
        with open(os.path.join(dest, "config.json"), "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
    except OSError as e:
        return False, "Couldn't write the add-on (%s)." % e
    return True, "Installed AnkiConnect. Quit Anki completely and reopen it."
