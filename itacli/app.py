"""Main loop: render the home screen, dispatch the menu. (SPECS §6, §13 step 0)"""
from . import db, state, ui, screens

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


def main():
    db.init_db()
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


if __name__ == "__main__":
    main()
