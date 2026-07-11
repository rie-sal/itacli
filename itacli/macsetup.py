"""One-time macOS setup for the capture hotkey + Apple Translate (SPECS §10).

The thin-invoker model: itacli exposes the `capture` command; the OS binds it
to a hotkey. On macOS the leanest native binder is an Automator Quick Action
plus a Services keyboard shortcut - nothing of ours stays resident.

Two steps genuinely require your click (Apple security; no app can do them
silently): adding the Translate Shortcut and binding the hotkey. Everything
else is prepared here. Run:  python3 run.py setup
"""
import os
import sys

from . import db, hotkeys, paths


def project_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def capture_command():
    """The exact shell command a binder should run."""
    return "%s %s capture" % (sys.executable, os.path.join(project_root(), "run.py"))


def write_helper():
    """Write an executable helper the Quick Action / Raycast can call."""
    setup_dir = os.path.join(paths.get_data_dir(), "setup")
    os.makedirs(setup_dir, exist_ok=True)
    script = os.path.join(setup_dir, "itacli-capture.command")
    with open(script, "w", encoding="utf-8") as f:
        f.write("#!/bin/bash\nexec %s\n" % capture_command())
    os.chmod(script, 0o755)
    return script


def guide_lines():
    hk = db.get_setting("capture_hotkey", "<cmd>+<shift>+i")
    try:
        pretty = hotkeys.human(hk)
    except ValueError:
        pretty = hk
    cmd = capture_command()
    tname = db.get_setting("translate_shortcut", "itacli Translate")
    return [
        "itacli - one-time macOS setup",
        "",
        "Your capture hotkey:   %s" % pretty,
        "Command it will run:   %s" % cmd,
        "",
        "1. Accessibility (needed to copy the selection in any app)",
        "   System Settings > Privacy & Security > Accessibility > add your",
        "   terminal (and Automator/Shortcuts) and toggle it on.",
        "",
        "2. Capture hotkey - Automator Quick Action (out-of-the-box)",
        "   a. Open Automator > New > Quick Action.",
        "   b. 'Workflow receives': no input, in: any application.",
        "   c. Add the action 'Run Shell Script' and paste:",
        "        %s" % cmd,
        "   d. Save as: itacli capture",
        "   e. System Settings > Keyboard > Keyboard Shortcuts > Services >",
        "      General > 'itacli capture' > assign %s" % pretty,
        "",
        "3. Apple Translate gloss - Shortcut named '%s'" % tname,
        "   a. Open Shortcuts > New Shortcut, name it exactly '%s'." % tname,
        "   b. Add 'Translate Text': from Italian to English,",
        "      text = Shortcut Input.",
        "   c. Add 'Stop and output' > Translated Text.",
        "   (Skip this and cards are still created; you add meanings in Anki.)",
        "",
        "A helper script was written to:",
        "   %s" % os.path.join(paths.get_data_dir(), "setup", "itacli-capture.command"),
        "Bind that instead if you prefer Raycast/skhd over a Quick Action.",
    ]


def run_setup(out=print):
    write_helper()
    for line in guide_lines():
        out(line)
