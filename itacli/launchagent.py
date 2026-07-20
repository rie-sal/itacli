"""Run the capture listener in the BACKGROUND (no terminal), via a macOS
LaunchAgent that starts at login and stays alive.

`itacli install-agent` writes ~/Library/LaunchAgents/com.itacli.capture.plist
and loads it; `itacli uninstall-agent` removes it. The background process still
needs Accessibility (macOS will prompt / add the python binary in
System Settings > Privacy & Security > Accessibility).
"""
import os
import subprocess
import sys

LABEL = "com.itacli.capture"


def _plist_path():
    return os.path.expanduser("~/Library/LaunchAgents/%s.plist" % LABEL)


def _project_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def install():
    import plistlib
    from . import paths
    logdir = paths.get_data_dir()
    plist = {
        "Label": LABEL,
        "ProgramArguments": [sys.executable, os.path.join(_project_root(), "run.py"),
                             "listen"],
        "RunAtLoad": True,
        "KeepAlive": True,
        "StandardOutPath": os.path.join(logdir, "agent.out.log"),
        "StandardErrorPath": os.path.join(logdir, "agent.err.log"),
    }
    os.makedirs(os.path.dirname(_plist_path()), exist_ok=True)
    with open(_plist_path(), "wb") as f:
        plistlib.dump(plist, f)
    subprocess.run(["launchctl", "unload", _plist_path()], capture_output=True)
    subprocess.run(["launchctl", "load", "-w", _plist_path()], capture_output=True)
    return _plist_path()


def uninstall():
    subprocess.run(["launchctl", "unload", "-w", _plist_path()], capture_output=True)
    if os.path.exists(_plist_path()):
        os.remove(_plist_path())
    return _plist_path()


def is_installed():
    return os.path.exists(_plist_path())
