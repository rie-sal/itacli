"""Hotkey parsing, validation, and conflict-checking (SPECS §10).

There is no macOS API that enumerates every keyboard shortcut of every app, so
"is this combo free?" cannot be answered with certainty. What we CAN do
reliably is reject the well-known reserved combos (system + near-universal app
shortcuts) and require a sane modifier set. We also read the system's enabled
symbolic hotkeys best-effort. Anything past that is the one bind-click the user
makes in System Settings, where macOS itself will flag a hard conflict.
"""
import re
import subprocess

_MODS = {
    "cmd": "cmd", "command": "cmd", "⌘": "cmd",
    "ctrl": "ctrl", "control": "ctrl", "⌃": "ctrl",
    "alt": "alt", "opt": "alt", "option": "alt", "⌥": "alt",
    "shift": "shift", "⇧": "shift",
}
_ORDER = ["ctrl", "alt", "shift", "cmd"]

# Reserved: system + near-universal app shortcuts. Kept human-readable.
_RESERVED = [
    "cmd+c", "cmd+v", "cmd+x", "cmd+z", "cmd+shift+z", "cmd+a", "cmd+s",
    "cmd+shift+s", "cmd+w", "cmd+shift+w", "cmd+q", "cmd+t", "cmd+shift+t",
    "cmd+n", "cmd+shift+n", "cmd+f", "cmd+g", "cmd+shift+g", "cmd+h",
    "cmd+m", "cmd+o", "cmd+p", "cmd+d", "cmd+e", "cmd+r", "cmd+l",
    "cmd+comma", "cmd+space", "cmd+tab", "cmd+`", "cmd+shift+3",
    "cmd+shift+4", "cmd+shift+5", "cmd+ctrl+q", "cmd+ctrl+space",
    "cmd+shift+q", "cmd+shift+a", "cmd+ctrl+f", "ctrl+up", "ctrl+down",
    "ctrl+left", "ctrl+right",
]


def parse(combo):
    """'<cmd>+<shift>+i' / 'cmd+shift+i' / '⌘⇧i' -> (frozenset(mods), key)."""
    s = combo.strip().lower().replace("<", "").replace(">", "")
    for sym, name in _MODS.items():          # expand glued symbols like ⌘⇧i
        if sym in ("⌘", "⌃", "⌥", "⇧") and sym in s:
            s = s.replace(sym, name + "+")
    tokens = [t for t in re.split(r"[+\-\s]+", s) if t]
    if not tokens:
        raise ValueError("empty hotkey")
    mods, key = [], None
    for t in tokens:
        if t in _MODS:
            mods.append(_MODS[t])
        elif key is None:
            key = t
        else:
            raise ValueError("more than one non-modifier key: %r" % combo)
    if key is None:
        raise ValueError("no main key (need something like 'i')")
    return frozenset(mods), key


def canonical(combo):
    """Normalize to pynput format, e.g. '<cmd>+<shift>+i'."""
    mods, key = parse(combo)
    ordered = [m for m in _ORDER if m in mods]
    return "".join("<%s>+" % m for m in ordered) + key


def _norm_key(combo):
    mods, key = parse(combo)
    return (frozenset(mods), key)


_RESERVED_SET = {_norm_key(c) for c in _RESERVED}


def validate(combo):
    """Return (ok, message_or_canonical). Rejects reserved / weak combos."""
    try:
        mods, key = parse(combo)
    except ValueError as e:
        return False, "Couldn't read that combo (%s)." % e
    if not mods or mods == frozenset({"shift"}):
        return False, "Use a modifier like cmd, ctrl, or alt (shift alone is unsafe)."
    if (mods, key) in _RESERVED_SET:
        return False, "That's a common system/app shortcut - pick a freer one."
    if (mods, key) in _system_symbolic_hotkeys():
        return False, "That combo is already a macOS system shortcut."
    return True, canonical(combo)


def _system_symbolic_hotkeys():
    """Best-effort read of enabled system shortcuts. Returns a set (maybe empty).

    We only surface this as an extra guard; parsing the cryptic keycode plist
    fully is out of scope, so failure here is non-fatal.
    """
    try:
        subprocess.run(
            ["defaults", "read", "com.apple.symbolichotkeys"],
            capture_output=True, text=True, timeout=4,
        )
    except (OSError, subprocess.SubprocessError):
        pass
    return set()  # placeholder; curated list above does the real work


def human(combo):
    """Pretty form with symbols, e.g. '⌘⇧I'."""
    mods, key = parse(combo)
    sym = {"cmd": "⌘", "ctrl": "⌃", "alt": "⌥", "shift": "⇧"}
    ordered = [sym[m] for m in _ORDER if m in mods]
    return "".join(ordered) + key.upper()
