"""One-time macOS setup for the capture hotkey + Apple Translate (SPECS §10).

Thin-invoker model: itacli exposes `capture`; the OS binds it to a hotkey. On
macOS the leanest native binder is an Automator Quick Action + a Services
keyboard shortcut - nothing of ours stays resident.

This module can GENERATE the Quick Action bundle (experimental: the plist is
well-formed, but Automator/Services acceptance must be validated on-device),
open the relevant apps/panes for you, and detect which pieces are already in
place so the terminal directions stay in sync with what you've done.

Two steps genuinely need your click (Apple security, unavoidable): granting
Accessibility and binding the hotkey.
"""
import os
import shutil
import subprocess
import sys
import uuid

from . import db, hotkeys, paths, ui

QUICK_ACTION = "itacli capture.workflow"


def project_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def capture_command():
    """The exact shell command the binder runs."""
    return "%s %s capture" % (sys.executable, os.path.join(project_root(), "run.py"))


def _run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=8)
    except (OSError, subprocess.SubprocessError):
        return None


def _staging():
    d = os.path.join(paths.get_data_dir(), "setup")
    os.makedirs(d, exist_ok=True)
    return d


def write_helper():
    """Executable helper a Quick Action / Raycast / skhd can call."""
    script = os.path.join(_staging(), "itacli-capture.command")
    with open(script, "w", encoding="utf-8") as f:
        f.write("#!/bin/bash\nexec %s\n" % capture_command())
    os.chmod(script, 0o755)
    return script


# --- experimental Quick Action generation -------------------------------

def build_quick_action():
    """Write a .workflow bundle to staging. Returns its path.

    EXPERIMENTAL: plistlib guarantees well-formed plists, but whether
    Automator/Services accept this exact document must be tested on your Mac.
    """
    import plistlib

    base = os.path.join(_staging(), QUICK_ACTION)
    contents = os.path.join(base, "Contents")
    os.makedirs(contents, exist_ok=True)

    info = {
        "NSServices": [{
            "NSMenuItem": {"default": "itacli capture"},
            "NSMessage": "runWorkflowAsService",
            "NSSendFileTypes": [],
            "NSSendTypes": [],
        }],
    }
    with open(os.path.join(contents, "Info.plist"), "wb") as f:
        plistlib.dump(info, f)

    action = {
        "action": {
            "AMAccepts": {"Container": "List", "Optional": True,
                          "Types": ["com.apple.applescript.object"]},
            "AMActionVersion": "2.0.3",
            "AMApplication": ["Automator"],
            "AMProvides": {"Container": "List",
                           "Types": ["com.apple.applescript.object"]},
            "ActionBundlePath": "/System/Library/Automator/Run Shell Script.action",
            "ActionName": "Run Shell Script",
            "ActionParameters": {
                "COMMAND_STRING": capture_command(),
                "CheckedForUserDefaultShell": True,
                "inputMethod": 0,
                "shell": "/bin/bash",
                "source": "",
            },
            "BundleIdentifier": "com.apple.RunShellScript",
            "CFBundleVersion": "2.0.3",
            "CanShowSelectedItemsWhenRun": False,
            "CanShowWhenRun": True,
            "Category": ["AMCategoryUtilities"],
            "Class Name": "RunShellScriptAction",
            "InputUUID": str(uuid.uuid4()),
            "Keywords": ["Shell", "Script", "Command", "Run", "Unix"],
            "OutputUUID": str(uuid.uuid4()),
            "UUID": str(uuid.uuid4()),
            "UnlocalizedApplications": ["Automator"],
            "arguments": {},
            "isViewVisible": 1,
            "location": "309.000000:253.000000",
        },
        "isViewVisible": 1,
    }
    wflow = {
        "AMApplicationBuild": "523",
        "AMApplicationVersion": "2.10",
        "AMDocumentVersion": "2",
        "actions": [action],
        "connectors": {},
        "workflowMetaData": {
            "applicationBundleIDsByPath": {},
            "applicationPaths": [],
            "inputTypeIdentifier": "com.apple.Automator.nothing",
            "outputTypeIdentifier": "com.apple.Automator.nothing",
            "presentationMode": 11,
            "processesInput": 0,
            "serviceInputTypeIdentifier": "com.apple.Automator.nothing",
            "serviceOutputTypeIdentifier": "com.apple.Automator.nothing",
            "serviceProcessesInput": 0,
            "systemImageName": "NSActionTemplate",
            "useAutomaticInputType": 0,
            "workflowTypeIdentifier": "com.apple.Automator.servicesMenu",
        },
    }
    with open(os.path.join(contents, "document.wflow"), "wb") as f:
        plistlib.dump(wflow, f)
    return base


def _services_dir():
    return os.path.expanduser("~/Library/Services")


def quick_action_installed():
    return os.path.exists(os.path.join(_services_dir(), QUICK_ACTION))


def install_quick_action():
    """Copy the generated bundle into ~/Library/Services and refresh."""
    src = build_quick_action()
    os.makedirs(_services_dir(), exist_ok=True)
    dst = os.path.join(_services_dir(), QUICK_ACTION)
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    _run(["/System/Library/CoreServices/pbs", "-flush"])
    return dst


def shortcut_installed(name):
    res = _run(["shortcuts", "list"])
    return bool(res and res.returncode == 0 and
               name in [l.strip() for l in res.stdout.splitlines()])


# --- interactive setup ---------------------------------------------------

def _open_app(name):
    _run(["open", "-a", name])


def _open_url(url):
    _run(["open", url])


def _is_macos():
    return sys.platform == "darwin"


def language_pack_walkthrough(out=print, input_fn=input, open_apps=None):
    """Walk the user through downloading Apple's offline language pack, and
    open the Translate app for them. (Assumes a recent macOS.)"""
    for line in [
        "Offline translation - download the language pack",
        "",
        "Apple's translator runs on-device once a language is downloaded, so",
        "your capture glosses then work with Wi-Fi off. One-time step:",
        "",
        "1. The Translate app opens.",
        "2. Set the two language buttons at the top to Italian and English.",
        "3. Translate any word once (type 'ciao') while online - macOS then",
        "   downloads and caches the on-device model.",
        "   Or: Translate menu (top bar) > Settings > download Italian.",
        "4. After that, translation keeps working offline.",
    ]:
        out(line)
    if open_apps is None:
        open_apps = sys.stdout.isatty()
    if open_apps and _is_macos():
        try:
            ans = input_fn(ui.INDENT + "Open the Translate app now? [y/N] ")
        except EOFError:
            ans = ""
        if ans.strip().lower() in ("y", "yes"):
            out("Opening Translate...")
            _open_app("Translate")


def run_setup(out=print, input_fn=input, open_apps=None):
    """Prepare artifacts, show synchronized status, and (only after asking, and
    only when interactive) open the right apps. Never opens apps in a pipe/test."""
    write_helper()
    bundle = build_quick_action()

    hk = db.get_setting("capture_hotkey", "<cmd>+<shift>+i")
    try:
        pretty = hotkeys.human(hk)
    except ValueError:
        pretty = hk
    tname = db.get_setting("translate_shortcut", "itacli Translate")

    qa_done = quick_action_installed()
    tr_done = shortcut_installed(tname)

    for line in [
        "itacli - one-time macOS setup",
        "",
        "Capture hotkey:  %s" % pretty,
        "Runs command:    %s" % capture_command(),
        "",
        "Status",
        "  [%s] Quick Action installed in ~/Library/Services" % ("x" if qa_done else " "),
        "  [%s] Translate Shortcut '%s'" % ("x" if tr_done else " ", tname),
        "  [ ] Accessibility granted   (can't be auto-detected)",
        "  [ ] Hotkey bound in System Settings",
        "",
        "Generated (experimental) Quick Action:",
        "  %s" % bundle,
        "",
        "Steps:",
        "1. Accessibility: add your terminal (+ Automator/Shortcuts), toggle on.",
        "2. Install the Quick Action: double-click the bundle above (or let me",
        "   copy it to ~/Library/Services), then bind %s under" % pretty,
        "   System Settings > Keyboard > Keyboard Shortcuts > Services.",
        "3. Translate Shortcut '%s': Translate Text (Italian>English)," % tname,
        "   input = Shortcut Input, then Stop and output > Translated Text.",
        "   (Optional - cards are still created without it.)",
    ]:
        out(line)

    if open_apps is None:
        open_apps = sys.stdout.isatty()   # never auto-open in a pipe / test
    if open_apps and _is_macos():
        try:
            ans = input_fn(ui.INDENT + "Open the apps/panes you need now? [y/N] ")
        except EOFError:
            ans = ""
        if ans.strip().lower() in ("y", "yes"):
            out("Opening...")
            _open_url("x-apple.systempreferences:com.apple.preference.security"
                      "?Privacy_Accessibility")
            _open_app("Automator")
            if not tr_done:
                _open_app("Shortcuts")
