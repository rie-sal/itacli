"""Stub screens for every menu entry. Each says what it will become and which
build step (SPECS §13) delivers it. As a pillar is built, its function here is
replaced by the real thing (or moved into its own module).
"""
from . import ui


def daily():
    ui.panel("Daily session", [
        "The adaptive session. The engine will pick today's mix from your",
        "weakest concepts and your time budget, then run each activity in",
        "sequence, log results, and update your Proficiency score.",
        "",
        "Build step: assembled after the individual pillars exist.",
    ])


def reading():
    from . import reading as reading_pillar
    reading_pillar.open_reading()


def grammar():
    ui.panel("Grammar", [
        "Scraped lessons and auto-graded exercises, concept by concept.",
        "Mastery per concept feeds the adaptive engine so you review what",
        "you actually struggle with.",
        "",
        "Build step 2: the most deterministic pillar.",
    ])


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
    ui.panel("Assessment & CEFR", [
        "Periodic, closed-form CEFR assessment (DIALANG-style; no speaking).",
        "Spaced by time studied, not calendar days. May reuse exercise-pool",
        "questions. Writing assessment planned for later.",
        "",
        "Build step 4.",
    ])


def progress():
    ui.panel("Progress & statistics", [
        "CEFR trend, the between-levels thermometer, concept-mastery heatmap,",
        "vocabulary growth, and time-on-task.",
        "",
        "Build step: grows alongside scoring and assessments.",
    ])


def library():
    ui.panel("Content library", [
        "View stored sources and how much unused content remains; trigger a",
        "scrape or refresh; add a source URL. When content runs low, the app",
        "scrapes for more.",
        "",
        "Build step: grows alongside each scraper.",
    ])


def settings():
    from . import db, anki
    while True:
        ui.clear()
        ui.blank()
        ui.line("Settings")
        ui.blank()
        ui.rule()
        ui.blank()
        ui.two_sided("1  Capture hotkey", db.get_setting("capture_hotkey"))
        ui.two_sided("2  Translate Shortcut (macOS)",
                     db.get_setting("translate_shortcut") or "(none)")
        ui.two_sided("3  Interests (for subreddits)",
                     db.get_setting("interests") or "(none)")
        ui.two_sided("4  Anki deck", db.get_setting("anki_deck"))
        ui.two_sided("   Anki status", "connected" if anki.is_available() else "offline")
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
        prompts = {
            "1": ("capture_hotkey",
                  "Hotkey (pynput format, e.g. <cmd>+<shift>+i): "),
            "2": ("translate_shortcut", "macOS Shortcut name (blank to disable): "),
            "3": ("interests", "Interests, comma-separated: "),
            "4": ("anki_deck", "Anki deck name: "),
        }
        if choice in prompts:
            key, prompt = prompts[choice]
            try:
                val = input(ui.INDENT + prompt).strip()
            except EOFError:
                return
            db.set_setting(key, val)
