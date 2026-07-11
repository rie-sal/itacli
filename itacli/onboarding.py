"""First-run setup: greet the learner (name, Pokemon-style), choose where data
lives, pick a valid capture hotkey, then hand off to macOS setup (SPECS §5, §10).
"""
import getpass
import os

from . import db, hotkeys, macsetup, paths, ui


def detect_name():
    """Best-effort first name from the system (macOS full name, else login)."""
    try:
        import pwd
        gecos = pwd.getpwuid(os.getuid()).pw_gecos.split(",")[0].strip()
        if gecos:
            return gecos.split()[0]
    except Exception:
        pass
    try:
        return getpass.getuser()
    except Exception:
        return "amico"


def run(input_fn=input):
    ui.clear()
    ui.blank()
    ui.slow("Benvenuto! Welcome to the world of itacli.")
    ui.blank()
    ui.slow("First - what should I call you?")
    ui.blank()

    guess = detect_name()
    ui.line("(I guessed: %s. Press Enter to keep it, or type a name.)" % guess)
    try:
        name = input_fn(ui.INDENT + "name: ").strip()
    except EOFError:
        name = ""
    name = name or guess
    ui.blank()
    ui.slow("Piacere, %s. Let's get you set up." % name)
    ui.blank()
    ui.rule()
    ui.blank()

    # 1. data location (skipped when a sandbox dir is forced via env)
    if paths._env_dir():
        db.init_db()
        ui.line("Sandbox data dir: %s" % paths.get_data_dir())
    else:
        default = paths.default_data_dir()
        ui.line("Where should your data (database + cached texts) live?")
        ui.line("Default: %s" % default)
        ui.blank()
        try:
            ans = input_fn(ui.INDENT + "path (Enter for default): ").strip()
        except EOFError:
            ans = ""
        chosen = paths.set_data_dir(ans or default)
        db.init_db()
        ui.blank()
        ui.line("Data dir: %s" % chosen)
    db.set_setting("user_name", name)
    ui.blank()

    # 2. capture hotkey (validated against reserved combos)
    ui.line("Choose your capture hotkey - the single do-everything shortcut.")
    ui.line("Format like:  cmd+shift+i   (needs a modifier; no reserved combos)")
    ui.blank()
    while True:
        try:
            raw = input_fn(ui.INDENT + "hotkey: ").strip()
        except EOFError:
            raw = ""
        if not raw:
            db.set_setting("capture_hotkey", "<cmd>+<shift>+i")
            ui.line("  using default cmd+shift+i")
            break
        ok, res = hotkeys.validate(raw)
        if ok:
            db.set_setting("capture_hotkey", res)
            ui.line("  set to %s" % hotkeys.human(res))
            break
        ui.line("  " + res)

    # 3. offline language pack (Apple on-device translation)
    ui.blank()
    ui.rule()
    ui.blank()
    macsetup.language_pack_walkthrough(out=ui.line, input_fn=input_fn)

    # 4. hand off to the one-time macOS setup
    macsetup.write_helper()
    ui.blank()
    ui.rule()
    ui.blank()
    ui.line("Almost there. For the one-time macOS hotkey + translate setup, run:")
    ui.line("   python3 run.py setup")
    ui.blank()
    try:
        input_fn(ui.INDENT + "press Enter to open itacli ")
    except EOFError:
        pass
