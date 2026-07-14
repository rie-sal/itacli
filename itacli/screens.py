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


def _lib_download(lib, book_id, title):
    ui.blank()
    ui.line("  Downloading Gutenberg #%s ..." % book_id)
    try:
        lib.add_gutenberg(book_id, title)
        ui.line("  added to your library.")
    except Exception as e:
        ui.line("  couldn't download: %s" % e)
    try:
        input(ui.INDENT + "  press Enter ")
    except EOFError:
        pass


def _lib_search_add(lib):
    try:
        q = input(ui.INDENT + "  Gutenberg ID or search terms: ").strip()
    except EOFError:
        return
    if not q:
        return
    if q.isdigit():
        _lib_download(lib, q, None)
        return
    try:
        results = lib.search_gutenberg(q)
    except RuntimeError as e:
        ui.line("  " + str(e))
        try:
            input(ui.INDENT + "  press Enter ")
        except EOFError:
            pass
        return
    ui.blank()
    for i, r in enumerate(results, 1):
        ui.line("  %d  %s - %s  (#%s)" % (i, r["title"][:40], r["author"][:22], r["id"]))
    if not results:
        ui.line("  no Italian results.")
        return
    try:
        pick = input(ui.INDENT + "  download which number? ").strip()
    except EOFError:
        return
    if pick.isdigit() and 1 <= int(pick) <= len(results):
        r = results[int(pick) - 1]
        _lib_download(lib, r["id"], r["title"])


def library():
    from . import library as lib, reading
    while True:
        ui.clear()
        ui.blank()
        ui.line("Content library")
        ui.blank()
        ui.rule()
        ui.blank()
        mine = lib.items()
        ui.line("Your texts:")
        if mine:
            for i, it in enumerate(mine, start=1):
                pct = reading._progress_pct(it["id"])
                ui.line("  %d  %s%s" % (i, it["title"],
                                        "  (%d%%)" % pct if pct is not None else ""))
        else:
            ui.line("  (empty - add one below, or drop .txt files in the folder)")
        ui.blank()
        ui.line("Suggested (Project Gutenberg, Italian):")
        for j, b in enumerate(reading.CURATED, start=1):
            ui.line("  s%d  %s - %s" % (j, b["title"], b["author"]))
        ui.blank()
        ui.line("[a] add by ID/search   [d N] delete text N   [q] back")
        ui.line("Folder: %s" % lib.folder())
        ui.blank()
        ui.rule()
        ui.blank()
        try:
            choice = input(ui.INDENT + "> ").strip().lower()
        except EOFError:
            return
        if choice in ("q", ""):
            return
        if choice == "a":
            _lib_search_add(lib)
        elif choice.startswith("s") and choice[1:].isdigit():
            idx = int(choice[1:]) - 1
            if 0 <= idx < len(reading.CURATED):
                b = reading.CURATED[idx]
                _lib_download(lib, b["id"], b["title"])
        elif choice.startswith("d"):
            num = choice[1:].strip()
            if num.isdigit() and 1 <= int(num) <= len(mine):
                lib.delete(mine[int(num) - 1]["file"])


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
