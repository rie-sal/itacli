"""Native-looking translation popover (compiles popover.swift on first use).

The system Translate popover can't be summoned programmatically (confirmed:
NSPerformService('Translate') fails, no such Service is registered), so this
shows itacli's own frosted floating panel with the translation instead.
"""
import os
import subprocess
import sys

from . import paths

_SRC = os.path.join(os.path.dirname(__file__), "popover.swift")


def _binary():
    """Compile popover.swift (cached in the data dir); return the binary path."""
    out = os.path.join(paths.get_data_dir(), "itacli_popover")
    try:
        if os.path.exists(out) and os.path.getmtime(out) >= os.path.getmtime(_SRC):
            return out
        r = subprocess.run(["swiftc", _SRC, "-o", out], capture_output=True, timeout=90)
        return out if r.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def show(message):
    """Show the floating panel with `message`. Non-blocking. True if shown."""
    if sys.platform != "darwin" or not message:
        return False
    b = _binary()
    if not b:
        return False
    try:
        subprocess.Popen([b, message], stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
        return True
    except (OSError, subprocess.SubprocessError):
        return False
