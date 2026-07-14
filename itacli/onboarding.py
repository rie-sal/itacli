"""First-run onboarding: greet + name (Pokemon-style), create the user profile,
pick a capture hotkey, route to Anki (create the deck), and hand off to the
one-time macOS setup (SPECS §5, §10). The app never starts without this.
"""
import getpass
import os
import subprocess
import sys

from . import anki, db, hotkeys, macsetup, paths, ui


def detect_name():
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


def _popup(message):
    if sys.stdout.isatty() and sys.platform == "darwin":
        try:
            subprocess.run(
                ["osascript", "-e",
                 'display dialog "%s" with title "itacli" buttons {"OK"} '
                 'default button "OK" giving up after 10 with icon note'
                 % message.replace('"', "'")],
                capture_output=True, timeout=12)
        except (OSError, subprocess.SubprocessError):
            pass


def _open(args):
    if sys.platform == "darwin" and sys.stdout.isatty():
        try:
            subprocess.run(args, capture_output=True, timeout=10)
        except (OSError, subprocess.SubprocessError):
            pass


def _anki_step(input_fn):
    deck = db.get_setting("anki_deck", "itacli")
    ui.blank()
    ui.rule()
    ui.blank()
    ui.line("Anki - your flashcards live here, so itacli must connect to it.")
    ui.line("Opening Anki and the AnkiConnect add-on page for you...")
    _open(["open", "-a", "Anki"])
    _open(["open", "https://ankiweb.net/shared/info/2055492159"])
    ui.blank()
    ui.line("In Anki:  Tools > Add-ons > Get Add-ons > paste  2055492159  > OK,")
    ui.line("then restart Anki. (I can't click inside Anki, but that's the step.)")
    while True:
        if anki.is_available():
            try:
                anki.ensure_deck(deck)
            except Exception:
                pass
            ui.blank()
            ui.line("Connected to Anki - created your deck '%s'!" % deck)
            _popup("itacli is connected to Anki and created your deck '%s'." % deck)
            return True
        ui.blank()
        try:
            c = input_fn(ui.INDENT + "[Enter] re-check  ·  [o] open Anki again  "
                         "·  [s] skip (not recommended): ").strip().lower()
        except EOFError:
            return False
        if c == "s":
            ui.line("Skipped. Saved words queue and sync once Anki + AnkiConnect run.")
            _popup("Anki isn't connected yet - saved words will queue and sync "
                   "once you finish AnkiConnect setup.")
            return False
        if c == "o":
            _open(["open", "-a", "Anki"])


def run(input_fn=input):
    ui.clear()
    ui.blank()
    ui.banner()
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

    # create/activate this user's profile, then initialise its DB
    if not paths._env_dir():
        paths.create_profile(name)
    db.init_db()
    db.set_setting("user_name", name)
    ui.blank()
    ui.slow("Piacere, %s. Let's get you set up." % name)

    # capture hotkey (validated)
    ui.blank()
    ui.rule()
    ui.blank()
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

    # offline language pack + Anki
    ui.blank()
    ui.rule()
    ui.blank()
    macsetup.language_pack_walkthrough(out=ui.line, input_fn=input_fn)
    _anki_step(input_fn)

    macsetup.write_helper()
    ui.blank()
    ui.rule()
    ui.blank()
    ui.line("For the one-time macOS hotkey + translate setup, run:  itacli setup")
    ui.blank()
    try:
        input_fn(ui.INDENT + "press Enter to open itacli ")
    except EOFError:
        pass
