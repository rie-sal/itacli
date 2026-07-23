"""Stub screens for every menu entry. Each says what it will become and which
build step (SPECS §13) delivers it. As a pillar is built, its function here is
replaced by the real thing (or moved into its own module).
"""
from . import ui


def daily():
    from . import daily as daily_pillar
    daily_pillar.open_daily()


def reading():
    from . import reading as reading_pillar
    reading_pillar.open_reading()


def grammar():
    from . import grammar as grammar_pillar
    grammar_pillar.open_grammar()


def vocabulary():
    from . import db, anki, sync
    while True:
        conn = db.connect()
        try:
            total = conn.execute("SELECT COUNT(*) FROM vocab").fetchone()[0]
            synced = conn.execute(
                "SELECT COUNT(*) FROM vocab WHERE anki_note_id IS NOT NULL").fetchone()[0]
            pending = conn.execute(
                "SELECT term, gloss FROM vocab WHERE anki_note_id IS NULL "
                "ORDER BY id DESC").fetchall()
        finally:
            conn.close()
        up = anki.is_available()
        ui.clear()
        ui.blank()
        ui.line("Vocabulary (Anki)")
        ui.blank()
        ui.rule()
        ui.blank()
        ui.two_sided("Words saved", str(total))
        ui.two_sided("Already in Anki", str(synced))
        ui.two_sided("Waiting for Anki", str(len(pending)))
        ui.two_sided("Anki", "connected" if up else "offline - open it to sync")
        ui.blank()
        if pending:
            ui.line("These are saved on your Mac and sync automatically once")
            ui.line("Anki is open (they are never lost):")
            ui.blank()
            for term, gloss in pending[:18]:
                ui.line("  %-18s %s" % (term, (gloss or "")[:45]))
            if len(pending) > 18:
                ui.line("  ...and %d more" % (len(pending) - 18))
        else:
            ui.line("All caught up - every saved word is in Anki.")
        ui.blank()
        ui.rule()
        ui.line("[s] sync now   [q] back")
        ui.blank()
        try:
            c = input(ui.INDENT + "> ").strip().lower()
        except EOFError:
            return
        if c in ("q", ""):
            return
        if c == "s":
            n = sync.flush()
            ui.line("  synced %d card(s)." % n if up else "  Anki is closed - open it first.")
            try:
                input(ui.INDENT + "  press Enter ")
            except EOFError:
                return


def listening():
    ui.panel("Listening", [
        "Native-speaker video and public-domain film with transcripts",
        "(yt-dlp). Launches mpv or a browser with the transcript synced in",
        "the terminal. Checks via transcript cloze / timestamp questions.",
        "",
        "Build step 5: the hardest pillar, built last.",
    ])


def assessment():
    from . import assessment as assess
    ui.clear()
    ui.blank()
    ui.line("Assessment & CEFR")
    ui.blank()
    ui.rule()
    ui.blank()
    ui.line("A short closed-form CEFR check (multiple choice, no speaking).")
    ui.line(assess.cadence_note())
    ui.blank()
    ui.line("Enter to start, q to go back.")
    ui.blank()
    ui.rule()
    ui.blank()
    try:
        choice = input(ui.INDENT + "> ").strip().lower()
    except EOFError:
        return
    if choice in ("q",):
        return
    assess.open_assessment()


def progress():
    from . import concepts, scoring, study, db
    ui.clear()
    ui.blank()
    ui.line("Progress & statistics")
    ui.blank()
    ui.rule()
    ui.blank()

    conn = db.connect()
    try:
        vocab = conn.execute("SELECT COUNT(*) FROM vocab").fetchone()[0]
        n_assess = conn.execute("SELECT COUNT(*) FROM assessments").fetchone()[0]
        last = conn.execute(
            "SELECT cefr_overall FROM assessments ORDER BY id DESC LIMIT 1"
        ).fetchone()
    finally:
        conn.close()
    frac, label, _ = scoring.proficiency_beta()

    ui.two_sided("CEFR level", (last[0] if last else "not assessed yet"))
    ui.two_sided("Proficiency", label)
    ui.two_sided("Assessments taken", str(n_assess))
    ui.two_sided("Vocabulary", "%d words" % vocab)
    ui.two_sided("Time studied", "%d min" % int(study.total_minutes()))
    ui.blank()
    ui.line("Grammar concepts  ( [x] mastered  [~] learning  [ ] not started )")
    ui.blank()
    for m in concepts.mastery():
        mark = {"mastered": "x", "learning": "~", "not started": " "}[m["status"]]
        acc = "%3d%%" % round(m["accuracy"] * 100) if m["accuracy"] is not None else "  -"
        ui.line("  [%s] %-24s %-3s  %s  (%d tries)"
                % (mark, m["name"], m["cefr"], acc, m["total"]))
    ui.blank()
    ui.rule()
    ui.blank()
    ui.line("Weak concepts show up more in Grammar (menu 3) until mastered.")
    try:
        input(ui.INDENT + "  press Enter ")
    except EOFError:
        return


_SAFE_HOTKEYS = ["ctrl+alt+cmd+space", "ctrl+alt+cmd+c", "ctrl+alt+cmd+i",
                 "ctrl+alt+cmd+z", "ctrl+alt+space", "ctrl+alt+c"]


def _hotkey_picker(db, hotkeys):
    """Suggest hotkeys mainstream apps rarely touch (Hyper combos), so the user
    doesn't trial-and-error into an app's shortcut."""
    ui.clear()
    ui.blank()
    ui.line("Choose your capture hotkey")
    ui.blank()
    ui.rule()
    ui.blank()
    ui.line("With itacli's background listener, ANY combo fires it. These are")
    ui.line("suggested because browsers/WhatsApp/Discord rarely use them:")
    ui.blank()
    valid = []
    for combo in _SAFE_HOTKEYS:
        ok, res = hotkeys.validate(combo)
        if ok:
            valid.append(res)
            ui.line("  %d   %s" % (len(valid), hotkeys.human(res)))
    ui.blank()
    ui.line("Pick a number, or type your own (e.g. cmd+shift+j), Enter to keep.")
    ui.blank()
    ui.rule()
    ui.blank()
    try:
        raw = input(ui.INDENT + "> ").strip()
    except EOFError:
        return
    if not raw:
        return
    if raw.isdigit() and 1 <= int(raw) <= len(valid):
        db.set_setting("capture_hotkey", valid[int(raw) - 1])
        return
    ok, res = hotkeys.validate(raw)
    if ok:
        db.set_setting("capture_hotkey", res)
    else:
        ui.line("  " + res)
        try:
            input(ui.INDENT + "  press Enter ")
        except EOFError:
            pass


def _users_screen():
    """List profiles; switch or create a new one. Returns True if the active
    profile changed (caller should reload)."""
    from . import paths, onboarding
    while True:
        ui.clear()
        ui.blank()
        ui.line("Users / profiles")
        ui.blank()
        ui.rule()
        ui.blank()
        profs = paths.list_profiles()
        active = paths.active_profile() or "default"
        for i, p in enumerate(profs, start=1):
            ui.line("  %d  %s%s" % (i, p, "  (active)" if p == active else ""))
        if not profs:
            ui.line("  (no profiles yet)")
        ui.blank()
        ui.line("[number] switch · [n] new user · [q] back")
        ui.blank()
        ui.rule()
        ui.blank()
        try:
            c = input(ui.INDENT + "> ").strip().lower()
        except EOFError:
            return False
        if c in ("q", ""):
            return False
        if c == "n":
            paths.reset_to_onboarding()
            onboarding.run()
            return True
        if c.isdigit() and 1 <= int(c) <= len(profs):
            paths.switch_profile(profs[int(c) - 1])
            return True


def settings():
    from . import db, anki, hotkeys, macsetup, paths, sync
    while True:
        ui.clear()
        ui.blank()
        ui.line("Settings")
        ui.blank()
        ui.rule()
        ui.blank()
        try:
            hk = hotkeys.human(db.get_setting("capture_hotkey"))
        except ValueError:
            hk = db.get_setting("capture_hotkey")
        ui.two_sided("1  Capture hotkey", hk)
        ui.two_sided("2  Translate Shortcut (macOS)",
                     db.get_setting("translate_shortcut") or "(none)")
        ui.two_sided("3  Interests (for subreddits)",
                     db.get_setting("interests") or "(none)")
        ui.two_sided("4  Anki deck", db.get_setting("anki_deck"))
        ui.two_sided("5  Users / switch profile",
                     "active: %s" % (paths.active_profile() or "default"))
        ui.two_sided("6  Re-run macOS setup guide", "")
        ui.two_sided("7  Your name", db.get_setting("user_name") or "(unset)")
        ui.two_sided("8  Start over (new user)", "")
        pend = sync.pending_count()
        status = "connected" if anki.is_available() else "offline"
        if pend:
            status += " · %d queued" % pend
        ui.two_sided("   Anki status", status)
        ui.blank()
        ui.line("Enter a number to change it, q to go back.")
        ui.blank()
        ui.rule()
        ui.blank()
        try:
            choice = input(ui.INDENT + "> ").strip().lower()
        except EOFError:
            return
        if choice in ("q", ""):
            return
        if choice == "1":
            _hotkey_picker(db, hotkeys)
        elif choice == "5":
            if _users_screen():
                return          # switched profile - reload menu fresh
        elif choice == "8":
            try:
                conf = input(ui.INDENT + "Onboard a NEW user now? [y/N]: ").strip().lower()
            except EOFError:
                continue
            if conf in ("y", "yes"):
                paths.reset_to_onboarding()
                from . import onboarding
                onboarding.run()
                return
        elif choice == "6":
            ui.clear()
            ui.blank()
            macsetup.run_setup(out=ui.line)
            ui.blank()
            try:
                input(ui.INDENT + "press Enter ")
            except EOFError:
                return
        else:
            prompts = {
                "2": ("translate_shortcut", "macOS Shortcut name (blank to disable): "),
                "3": ("interests", "Interests, comma-separated: "),
                "4": ("anki_deck", "Anki deck name: "),
                "7": ("user_name", "Your name: "),
            }
            if choice in prompts:
                key, prompt = prompts[choice]
                try:
                    val = input(ui.INDENT + prompt).strip()
                except EOFError:
                    return
                db.set_setting(key, val)
