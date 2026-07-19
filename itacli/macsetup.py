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
    """Launch an app by name. Returns True only if it actually launched."""
    res = _run(["open", "-a", name])
    return bool(res and res.returncode == 0)


def _open_url(url):
    _run(["open", url])


def _is_macos():
    return sys.platform == "darwin"


def _app_available(name):
    """True if an app of this name is known to LaunchServices (does not launch)."""
    res = _run(["osascript", "-e", 'POSIX path of (path to application "%s")' % name])
    return bool(res and res.returncode == 0)


def language_pack_walkthrough(out=print, input_fn=input, open_apps=None):
    """Guide the user to get Apple's offline language model. Works whether or
    not the standalone Translate app exists on this Mac."""
    has_translate = _is_macos() and _app_available("Translate")
    lines = [
        "Offline translation - get the on-device language model",
        "",
        "Apple's translator runs on-device once the Italian model is",
        "downloaded, so your capture glosses then work with Wi-Fi off.",
        "",
        "Most reliable: after you create the 'itacli Translate' Shortcut",
        "(setup step 3), run it ONCE while online - macOS downloads the",
        "Italian model the first time, then it works offline forever.",
    ]
    if has_translate:
        lines += [
            "",
            "You also have the Translate app: open it, set the two language",
            "buttons to Italian and English, and it can manage downloads too.",
        ]
    else:
        lines += [
            "",
            "(This Mac has no standalone Translate app - that's fine; the",
            "Shortcut route above is all you need.)",
        ]
    for line in lines:
        out(line)

    if open_apps is None:
        open_apps = sys.stdout.isatty()
    if open_apps and has_translate:
        try:
            ans = input_fn(ui.INDENT + "Open the Translate app now? [y/N] ")
        except EOFError:
            ans = ""
        if ans.strip().lower() in ("y", "yes"):
            if _open_app("Translate"):
                out("Opening Translate...")
            else:
                out("Could not open Translate - use the Shortcut route above.")


def _reveal(path):
    if os.path.exists(path):
        _run(["open", "-R", path])


def _terminal_app_path():
    known = {
        "Apple_Terminal": "/System/Applications/Utilities/Terminal.app",
        "iTerm.app": "/Applications/iTerm.app",
        "vscode": "/Applications/Visual Studio Code.app",
        "WarpTerminal": "/Applications/Warp.app",
        "Hyper": "/Applications/Hyper.app",
        "WezTerm": "/Applications/WezTerm.app",
    }
    return known.get(os.environ.get("TERM_PROGRAM", ""))


def _accessibility_apps():
    apps = []
    tp = _terminal_app_path()
    if tp:
        apps.append(tp)
    apps.append("/System/Applications/Automator.app")
    return apps


def _step(out, input_fn, act, title, short_lines, eli5_lines, do):
    out("")
    out("--- %s ---" % title)
    for l in short_lines:
        out("  " + l)
    if act and do:
        do()
    while True:
        try:
            c = input_fn(ui.INDENT + "[Enter] done, next  ·  [?] explain step by "
                         "step  ·  [o] re-open  ·  [s] skip: ").strip().lower()
        except EOFError:
            return
        if c in ("?", "e", "help"):
            out("")
            for l in eli5_lines:
                out("  " + l)
            continue
        if c == "o":
            if act and do:
                do()
            continue
        return


def _concise_guide(pretty, tname):
    return [
        "One-time setup - run  itacli setup  in a terminal to do this guided.",
        "1. Accessibility: add your terminal + Automator and toggle them ON.",
        "2. Bind %s to 'itacli capture' under System Settings > Keyboard >" % pretty,
        "   Keyboard Shortcuts > Services > General.",
        "3. Create a Shortcut named '%s' (Translate Text, Italian>English," % tname,
        "   input = Shortcut Input). Then: itacli test-translate ciao",
    ]


def run_setup(out=print, input_fn=input, open_apps=None):
    """Guided macOS setup: auto-installs the Quick Action, opens/reveals the
    exact apps, and offers per-step ELI5 explanations. Never touches the OS in a
    pipe/test."""
    write_helper()
    hk = db.get_setting("capture_hotkey", "<cmd>+<shift>+i")
    try:
        pretty = hotkeys.human(hk)
    except ValueError:
        pretty = hk
    tname = db.get_setting("translate_shortcut", "itacli Translate")

    act = _is_macos() and (open_apps if open_apps is not None else sys.stdout.isatty())

    out("itacli - one-time setup for your capture hotkey  (%s)" % pretty)
    out("")

    if not act:
        for l in _concise_guide(pretty, tname):
            out(l)
        return

    # (2b) default to installing the Quick Action for the user
    try:
        install_quick_action()
        out("Done: installed your capture Quick Action into ~/Library/Services.")
    except Exception as e:
        out("(Couldn't auto-install the Quick Action: %s - not fatal.)" % e)
    out("Three quick steps. Press [?] on any step for a plain-English walk-through.")

    acc_apps = _accessibility_apps()

    def do_accessibility():
        _open_url("x-apple.systempreferences:com.apple.preference.security"
                  "?Privacy_Accessibility")
        for a in acc_apps:
            _reveal(a)

    _step(out, input_fn, act, "Step 1 of 3: Accessibility",
          ["This lets itacli press Cmd-C for you in any app.",
           "I opened Accessibility settings + a Finder window with the apps.",
           "Add these to the list and switch each ON:"] + ["   " + a for a in acc_apps],
          ["Why: macOS won't let a program use your keyboard until you allow it.",
           "Step by step:",
           "  1. In the Accessibility list, click the small '+' button.",
           "  2. A file window opens. Press  Cmd-Shift-G  (a 'go to folder' box).",
           "  3. Paste one of these paths, press Return, then click Open:"]
          + ["        " + a for a in acc_apps]
          + ["  4. Back in the list, flip its switch ON (turns blue).",
             "  5. Do the same for each app listed above.",
             "Easier: I opened them in Finder - just DRAG each into the list.",
             "Also: the first time your hotkey fires, macOS may pop up asking for",
             "this - if so, just click Allow / Open System Settings."],
          do_accessibility)

    _step(out, input_fn, act, "Step 2 of 3: Bind your hotkey",
          ["Your capture Quick Action is installed; now give it the hotkey %s." % pretty,
           "I opened Keyboard settings."],
          ["Why: this is what makes %s trigger itacli everywhere." % pretty,
           "Step by step:",
           "  1. In Keyboard settings, click 'Keyboard Shortcuts...'.",
           "  2. Select 'Services' in the left list.",
           "  3. Open the 'General' group; find 'itacli capture'.",
           "  4. Double-click 'none' to its right, then press  %s ." % pretty],
          lambda: _open_url("x-apple.systempreferences:com.apple.Keyboard-Settings.extension"))

    _step(out, input_fn, act, "Step 3 of 3: Translate Shortcut (optional)",
          ["For automatic translations, make a Shortcut named '%s'." % tname,
           "I opened Shortcuts. (Cards still save without this.)"],
          ["Why: this gives itacli Apple's translator for word glosses.",
           "Step by step:",
           "  1. In Shortcuts, click '+' (new shortcut). Name it exactly:",
           "        %s" % tname,
           "  2. Search actions for 'Translate Text'; add it.",
           "  3. Set it to translate from Italian to English.",
           "  4. Right-click (control-click / two-finger click) the text box in",
           "     that action and choose 'Shortcut Input' - that's the word",
           "     itacli hands to it.",
           "  5. Click the settings button (sliders icon, top of the shortcut)",
           "     and set 'Receive' to 'Text' - this lets itacli pass the word in.",
           "  6. Save it. The first time it runs while online, macOS downloads",
           "     the Italian model once; after that it works offline.",
           "  Check it worked:  itacli test-translate ciao"],
          lambda: _open_app("Shortcuts"))

    out("")
    out("All set - %s now captures, translates, and saves cards." % pretty)
