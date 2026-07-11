"""Where user data lives (SPECS §5). Chosen at first run, changeable in
Settings. A tiny bootstrap file at ~/.itacli.json remembers the location; the
SQLite DB and content cache live inside it.
"""
import json
import os
import sys

APP = "itacli"


def _env_dir():
    """Test/sandbox override: ITACLI_DATA_DIR wins over the bootstrap file, so
    a throwaway run never touches your real data."""
    return os.environ.get("ITACLI_DATA_DIR")


def _bootstrap_path():
    return os.path.join(os.path.expanduser("~"), ".itacli.json")


def default_data_dir():
    home = os.path.expanduser("~")
    if sys.platform == "darwin":
        return os.path.join(home, "Library", "Application Support", APP)
    return os.path.join(home, ".local", "share", APP)


def _load():
    p = _bootstrap_path()
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}
    return {}


def is_first_run():
    if _env_dir():
        return not os.path.exists(os.path.join(_env_dir(), "itacli.db"))
    return "data_dir" not in _load()


def get_data_dir():
    d = _env_dir() or _load().get("data_dir") or default_data_dir()
    os.makedirs(d, exist_ok=True)
    return d


def set_data_dir(path, move_existing=True):
    """Point itacli at `path`. Optionally move an existing DB there."""
    new = os.path.abspath(os.path.expanduser(path.strip()))
    os.makedirs(new, exist_ok=True)
    old = _load().get("data_dir")
    if move_existing and old and old != new:
        old_db = os.path.join(old, "itacli.db")
        new_db = os.path.join(new, "itacli.db")
        if os.path.exists(old_db) and not os.path.exists(new_db):
            os.replace(old_db, new_db)
    data = _load()
    data["data_dir"] = new
    with open(_bootstrap_path(), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return new


def db_path():
    return os.path.join(get_data_dir(), "itacli.db")


def content_cache():
    d = os.path.join(get_data_dir(), "content_cache")
    os.makedirs(d, exist_ok=True)
    return d
