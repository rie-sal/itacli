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
    "8": screens.library,
    "9": screens.settings,
}


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
        action = MENU.get(choice)
        if action:
            action()
    ui.clear()
    print("\n" + ui.INDENT + "Buon studio.\n")


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv

    if argv:
        # commands run headless; ensure a data dir exists without onboarding
        if paths.is_first_run():
            paths.set_data_dir(paths.default_data_dir())
        db.init_db()
        cmd, rest = argv[0], argv[1:]
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
        print("Unknown command: %s" % cmd)
        return

    if paths.is_first_run():
        from . import onboarding
        onboarding.run()
    db.init_db()
    menu_loop()


if __name__ == "__main__":
    main()
