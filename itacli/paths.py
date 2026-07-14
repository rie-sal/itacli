"""Data location + user profiles (SPECS §5).

Each user is a PROFILE - a named folder holding its own DB, cache, and library.
This lets you keep multiple save-files (and, later, one per language). The
active profile is remembered in a tiny bootstrap file at ~/.itacli.json. The DB
and content live inside the active profile's folder.

ITACLI_DATA_DIR overrides everything with a single explicit folder (used for
sandbox/testing); profiles are bypassed in that mode.
"""
import json
import os
import re
import sys

APP = "itacli"


def _env_dir():
    return os.environ.get("ITACLI_DATA_DIR")


def _bootstrap_path():
    return os.path.join(os.path.expanduser("~"), ".itacli.json")


def _base_dir():
    home = os.path.expanduser("~")
    if sys.platform == "darwin":
        return os.path.join(home, "Library", "Application Support", APP)
    return os.path.join(home, ".local", "share", APP)


def _profiles_dir():
    return os.path.join(_base_dir(), "profiles")


def _load():
    p = _bootstrap_path()
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}
    return {}


def _save(data):
    with open(_bootstrap_path(), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def slug(name):
    s = re.sub(r"[^a-z0-9]+", "-", (name or "").strip().lower()).strip("-")
    return s or "user"


def active_profile():
    return _load().get("active_profile")


def list_profiles():
    d = _profiles_dir()
    return sorted(x for x in os.listdir(d)) if os.path.isdir(d) else []


def get_data_dir():
    if _env_dir():
        os.makedirs(_env_dir(), exist_ok=True)
        return _env_dir()
    prof = active_profile() or "default"
    d = os.path.join(_profiles_dir(), prof)
    os.makedirs(d, exist_ok=True)
    return d


def is_first_run():
    """True until an active profile exists with an initialised DB."""
    if _env_dir():
        return not os.path.exists(os.path.join(_env_dir(), "itacli.db"))
    prof = active_profile()
    if not prof:
        return True
    return not os.path.exists(os.path.join(_profiles_dir(), prof, "itacli.db"))


def create_profile(name):
    """Create (or reuse) a profile and make it active. Returns its folder."""
    s = slug(name)
    d = os.path.join(_profiles_dir(), s)
    os.makedirs(d, exist_ok=True)
    data = _load()
    data["active_profile"] = s
    _save(data)
    return d


def switch_profile(s):
    data = _load()
    data["active_profile"] = s
    _save(data)


def reset_to_onboarding():
    """Forget the active profile so the next launch onboards (data kept)."""
    data = _load()
    data.pop("active_profile", None)
    _save(data)


def db_path():
    return os.path.join(get_data_dir(), "itacli.db")


def content_cache():
    d = os.path.join(get_data_dir(), "content_cache")
    os.makedirs(d, exist_ok=True)
    return d


def library_dir():
    d = os.path.join(get_data_dir(), "library")
    os.makedirs(d, exist_ok=True)
    return d
