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
    ui.panel("Vocabulary (Anki)", [
        "All cards live in Anki. The app pushes cards and reads review",
        "stats back. Quick-add without a GUI:  add \"magari\" \"maybe / if only\"",
        "The global hotkey captures a word from any app, chunks the",
        "sentence, dedupes, and smart-saves the relevant cards.",
        "",
        "Build step 3: Anki bridge + beta Proficiency score.",
    ])


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


def library():
    ui.panel("Content library", [
        "View stored sources and how much unused content remains; trigger a",
        "scrape or refresh; add a source URL. When content runs low, the app",
        "scrapes for more.",
        "",
        "Build step: grows alongside each scraper.",
    ])


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
        ui.two_sided("5  Data location", paths.get_data_dir())
        ui.two_sided("6  Re-run macOS setup guide", "")
        ui.two_sided("7  Your name", db.get_setting("user_name") or "(unset)")
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
            while True:
                try:
                    raw = input(ui.INDENT + "Hotkey (e.g. cmd+shift+i, blank to keep): ").strip()
                except EOFError:
                    break
                if not raw:
                    break
                ok, res = hotkeys.validate(raw)
                if ok:
                    db.set_setting("capture_hotkey", res)
                    break
                ui.line("  " + res)
        elif choice == "5":
            try:
                newdir = input(ui.INDENT + "New data location (blank to keep): ").strip()
            except EOFError:
                continue
            if newdir:
                paths.set_data_dir(newdir)
                db.init_db()
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
