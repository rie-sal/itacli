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
    ui.panel("Reading", [
        "Read public-domain literature, Wikisource, and native-speaker",
        "subreddits chosen from your interests. Highlight unknown words to",
        "save them; comprehension via supplied questions or auto cloze.",
        "",
        "Build step 1 (the spine): Reading + highlight -> Anki.",
    ])


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
    ui.panel("Settings", [
        "Daily time budget, activity ratio (auto or manual), goals and",
        "interests (which drive subreddit selection), Anki connection,",
        "dictionary / translation engine, and LLM API key for opt-in features.",
        "",
        "Build step: expanded as options appear.",
    ])
