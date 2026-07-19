"""Grammar pillar (SPECS §7-grammar): deterministic fill-in-the-blank drills.

Exercises are generated from grammar-concept templates + your tagged vocab, so
they always use words you're actually learning and the answer is correct by
construction. The pillar stays LOCKED until you have enough tagged vocab for
the engine to draw on.
"""
import datetime
import random

from . import concepts, db, study, templates, ui

# Which catalogue concept each drill template trains.
TEMPLATE_KEY = {"def-art": "articles", "indef-art": "articles",
                "plural": "noun-plural", "present": "present-tense"}

MIN_TAGGED = 6   # usable tagged words needed before grammar unlocks


def _usable_items():
    """Vocab the templates can draw on: nouns with gender + verbs (with lemma)."""
    conn = db.connect()
    try:
        rows = conn.execute(
            "SELECT term, pos, gender, lemma FROM vocab "
            "WHERE (pos = 'noun' AND gender IN ('m','f')) OR pos = 'verb'"
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def _record(concept, correct):
    conn = db.connect()
    try:
        conn.execute(
            "INSERT INTO attempts(content_item_id, correct, timestamp, concept_tags) "
            "VALUES (NULL, ?, ?, ?)",
            (1 if correct else 0,
             datetime.datetime.now().isoformat(timespec="seconds"),
             "grammar:%s" % concept),
        )
        conn.commit()
    finally:
        conn.close()


def _pool():
    """All (template, item) exercises the current vocab can produce."""
    pool = []
    for item in _usable_items():
        for t in templates.buildable(item):
            pool.append((t, item))
    return pool


def open_grammar():
    items = _usable_items()
    if len(items) < MIN_TAGGED:
        ui.panel("Grammar - locked", [
            "Grammar drills are generated from words you're learning, so the",
            "engine needs some tagged vocabulary first.",
            "",
            "Usable tagged words: %d / %d needed." % (len(items), MIN_TAGGED),
            "",
            "Read (menu 2) and save unknown words, or use the capture hotkey.",
            "Nouns (with gender) and verbs get tagged automatically.",
        ])
        return

    from . import grammar_selector
    exercises = grammar_selector.select(8)
    if not exercises:
        ui.panel("Grammar", [
            "You have tagged vocab, but none of it fits the current drills yet,",
            "or you've mastered everything available. Save a few more words.",
        ])
        return

    with study.Timer():
        _drill(exercises)


def _drill(exercises):
    asked = right = 0
    for ex in exercises:
        asked += 1
        ui.clear()
        ui.blank()
        ui.two_sided("Grammar · %s" % ex["concept"].replace("-", " "), "")
        ui.blank()
        ui.rule()
        ui.blank()
        ui.line(ex["prompt"])
        ui.blank()
        try:
            guess = input(ui.INDENT + "  = ").strip()
        except EOFError:
            return
        if guess.lower() in ("q", "quit"):
            break
        correct = guess.strip().lower() == ex["answer"].lower()
        right += correct
        _record(ex["concept"], correct)
        ui.blank()
        if correct:
            ui.line("  correct!  (%s)" % ex["note"])
        else:
            ui.line("  answer: %s   (%s)" % (ex["answer"], ex["note"]))
        try:
            input(ui.INDENT + "  press Enter ")
        except EOFError:
            return

    ui.panel("Grammar - session done", [
        "Score: %d / %d correct." % (right, asked),
        "Weak concepts get shown more as tracking improves.",
    ])
