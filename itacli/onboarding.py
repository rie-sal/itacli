"""First-run setup: choose where data lives, pick a valid capture hotkey,
then point the user at the one-time macOS setup (SPECS §5, §10)."""
from . import db, hotkeys, macsetup, paths, ui


def run(input_fn=input):
    ui.clear()
    ui.blank()
    ui.line("Benvenuto - welcome to itacli.")
    ui.blank()
    ui.rule()
    ui.blank()

    # 1. data location
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

    # 3. hand off to the one-time macOS setup
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
