"""Main loop + command dispatch. (SPECS §6, §13 step 0)

    python3 run.py              open the menu
    python3 run.py listen       run the capture-hotkey daemon
    python3 run.py capture      run one capture cycle (bind to any key)
    python3 run.py add FRONT BACK   quick-add a card to Anki
"""
import sys

from . import db, paths, state, ui, screens

MENU = {
    "1": screens.daily,
    "2": screens.reading,
    "3": screens.grammar,
    "4": screens.vocabulary,
    "5": screens.listening,
    "6": screens.assessment,
    "7": screens.progress,
    "9": screens.settings,
}


def _set_time():
    cur = int(float(db.get_setting("time_budget_min", "30")))
    try:
        raw = input(ui.INDENT + "Minutes you have today [%d]: " % cur).strip()
    except EOFError:
        return
    if raw.isdigit() and int(raw) > 0:
        db.set_setting("time_budget_min", str(int(raw)))


def _quick_add(args):
    from . import anki
    if len(args) < 1:
        print('usage: python3 run.py add "term" "meaning"')
        return
    front = args[0]
    back = args[1] if len(args) > 1 else ""
    if not anki.is_available():
        print("Anki not reachable - open Anki (with AnkiConnect) and retry.")
        return
    note_id = anki.add_card(front, back)
    print("Added: %s" % front if note_id else "Not added (duplicate?): %s" % front)


def menu_loop():
    while True:
        ui.home(state.home_data())
        try:
            choice = input(ui.INDENT + "> ").strip().lower()
        except EOFError:
            break
        if choice in ("q", "quit", "exit"):
            break
        if choice == "t":
            _set_time()
            continue
        action = MENU.get(choice)
        if action:
            action()
    ui.clear()
    print("\n" + ui.INDENT + "Buon studio.\n")


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv

    if argv:
        db.init_db()          # get_data_dir auto-creates the profile folder
        cmd, rest = argv[0], argv[1:]
        if cmd == "reset":
            paths.reset_to_onboarding()
            print("Reset. The next launch will start onboarding a new user.")
            return
        if cmd == "anki-check":
            from . import anki, sync
            if anki.is_available():
                print("Anki: connected (AnkiConnect on :8765).")
                pushed = sync.flush()
                print("Synced %d queued card(s)." % pushed if pushed
                      else "Nothing queued.")
            else:
                print("Anki: NOT reachable. Open Anki and install the AnkiConnect")
                print("add-on (Tools > Add-ons > Get Add-ons > code 2055492159),")
                print("then restart Anki. %d card(s) are queued and will sync."
                      % sync.pending_count())
            return
        if cmd == "listen":
            from . import capture
            return capture.listen()
        if cmd == "capture":
            from . import capture
            return capture.capture_once()
        if cmd == "setup":
            from . import macsetup
            return macsetup.run_setup()
        if cmd == "package":
            from . import packaging
            dest = packaging.build_zip(rest[0] if rest else None)
            print("Wrote test zip: %s" % dest)
            return
        if cmd == "add":
            return _quick_add(rest)
        if cmd == "install-launcher":
            from . import launcher
            path, on_path = launcher.install_launcher()
            print("Installed launcher: %s" % path)
            if on_path:
                print("Run the app any time by typing:  itacli")
            else:
                print("Added ~/.local/bin to PATH in your shell profile.")
                print("Open a new terminal (or `source ~/.zshrc`), then: itacli")
            return
        if cmd == "test-translate":
            from . import capture, db as _db
            word = rest[0] if rest else "ciao"
            name = _db.get_setting("translate_shortcut", "")
            installed = name in capture._installed_shortcuts()
            print("Translate Shortcut: %r  (installed: %s)" % (name, installed))
            result = capture.translate(word)
            if result:
                print("  %s -> %s   ✓ translation works" % (word, result))
            elif not installed:
                print("  Shortcut not found. Create it in Shortcuts.app (see"
                      " `run.py setup`), then retry.")
            else:
                print("  No output - check the Shortcut has a Translate Text"
                      " action with input = Shortcut Input.")
            return
        print("Unknown command: %s" % cmd)
        return

    if paths.is_first_run():
        from . import onboarding
        onboarding.run()
    else:
        db.init_db()
        if not db.get_setting("user_name"):
            from . import onboarding
            onboarding.run()
    db.init_db()
    from . import sync
    pushed = sync.flush()          # drain the offline queue if Anki is up
    if pushed:
        print(ui.INDENT + "Synced %d queued card(s) to Anki." % pushed)
    menu_loop()


if __name__ == "__main__":
    main()
