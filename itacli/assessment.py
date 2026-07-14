"""CEFR assessment (SPECS §9): closed-form, auto-graded, no speaking.

Administers CEFR-tagged items and estimates a band as the highest contiguous
level passed. Answers can be MULTIPLE-CHOICE or FREE-RESPONSE (toggle while
answering); "I don't know" is always an option (recorded honestly, not a
guess). Every grammar item's result is logged to `attempts` so it feeds
concept mastery (concepts.py) and the Proficiency score (scoring.py).
"""
import datetime
import random

from . import assessment_items as bank
from . import db, study, ui

PASS = 0.6   # fraction correct to "pass" a level


def _norm(s):
    return s.strip().lower().strip(".,;:!?\"'()[]«»…")


def _ask(item, index, total, mode):
    ui.clear()
    ui.blank()
    ui.two_sided("CEFR assessment (%s)" % ("multiple choice" if mode == "mc"
                                           else "free response"),
                 "%d / %d" % (index, total))
    ui.blank()
    ui.rule()
    ui.blank()
    ui.line(item["q"])
    ui.blank()
    if mode == "mc":
        choices = list(item["choices"])
        random.shuffle(choices)
        for i, c in enumerate(choices, start=1):
            ui.line("  %d  %s" % (i, c))
        ui.blank()
        ui.line("[number] answer · [d] don't know · [f] free-response · [q] stop")
        try:
            raw = input(ui.INDENT + "  > ").strip().lower()
        except EOFError:
            return None, "stop"
        if raw in ("q", "quit"):
            return None, "stop"
        if raw == "f":
            return None, "toggle"
        if raw == "d":
            return False, "answer"
        if raw.isdigit() and 1 <= int(raw) <= len(choices):
            return choices[int(raw) - 1] == item["answer"], "answer"
        return False, "answer"
    else:
        ui.line("[type answer] · [d] don't know · [c] multiple-choice · [q] stop")
        try:
            raw = input(ui.INDENT + "  = ").strip()
        except EOFError:
            return None, "stop"
        low = raw.lower()
        if low in ("q", "quit"):
            return None, "stop"
        if low == "c":
            return None, "toggle"
        if low == "d" or not raw:
            return False, "answer"
        return _norm(raw) == _norm(item["answer"]), "answer"


def _estimate(level_scores):
    passed = None
    for lvl in bank.LEVELS:
        total, correct = level_scores.get(lvl, (0, 0))
        if total and correct / total >= PASS:
            passed = lvl
        else:
            break
    return passed


def _log_item(item, correct):
    """Feed each grammar item into attempts -> concept mastery + proficiency."""
    concept = bank.CONCEPT_BY_ID.get(item["id"])
    tag = "grammar:%s" % concept if concept else "cefr:%s" % item["skill"]
    conn = db.connect()
    try:
        conn.execute(
            "INSERT INTO attempts(content_item_id, correct, timestamp, concept_tags) "
            "VALUES (NULL, ?, ?, ?)",
            (1 if correct else 0,
             datetime.datetime.now().isoformat(timespec="seconds"), tag),
        )
        conn.commit()
    finally:
        conn.close()


def _store(overall, per_skill, item_ids):
    conn = db.connect()
    try:
        conn.execute(
            "INSERT INTO assessments(timestamp, study_minutes_at_time, "
            "cefr_reading, cefr_listening, cefr_grammar, cefr_vocabulary, "
            "cefr_overall, item_ids_used) VALUES (?,?,?,?,?,?,?,?)",
            (datetime.datetime.now().isoformat(timespec="seconds"),
             int(study.total_minutes()), None, None,
             per_skill.get("grammar"), per_skill.get("vocabulary"),
             overall, ",".join(item_ids)),
        )
        conn.commit()
    finally:
        conn.close()
    study.mark_assessed()


def open_assessment():
    items = bank.ITEMS
    level_scores = {lvl: [0, 0] for lvl in bank.LEVELS}
    skill_scores = {}
    asked_ids = []
    mode = db.get_setting("assessment_mode", "mc")

    with study.Timer():
        for idx, item in enumerate(items, start=1):
            while True:
                result, action = _ask(item, idx, len(items), mode)
                if action == "stop":
                    ui.panel("CEFR assessment", [
                        "Stopped early - no score recorded.",
                        "Run it again when you have a few minutes."])
                    return
                if action == "toggle":
                    mode = "free" if mode == "mc" else "mc"
                    db.set_setting("assessment_mode", mode)
                    continue
                break
            asked_ids.append(item["id"])
            level_scores[item["cefr"]][0] += 1
            level_scores[item["cefr"]][1] += int(result)
            s = skill_scores.setdefault(item["skill"], [0, 0])
            s[0] += 1
            s[1] += int(result)
            _log_item(item, result)

    ls = {lvl: (t, c) for lvl, (t, c) in level_scores.items()}
    overall = _estimate(ls) or "pre-A1"
    per_skill = {sk: (_estimate(ls) or "A1<") for sk in skill_scores}
    _store(overall if overall != "pre-A1" else "A1<", per_skill, asked_ids)

    lines = ["Your estimated CEFR level:  %s" % overall, ""]
    for lvl in bank.LEVELS:
        t, c = ls[lvl]
        if t:
            lines.append("  %s   %d / %d correct" % (lvl, c, t))
    lines += ["", "Mistakes now feed your grammar concept tracker (menu 7)",
              "and your Proficiency score. Take it again anytime."]
    ui.panel("CEFR assessment - done", lines)


def cadence_note():
    if study.assessment_due():
        return "A CEFR check is recommended now (you've studied enough since the last)."
    remaining = study.ASSESS_EVERY_MIN - study.minutes_since_last_assessment()
    return "Next CEFR check recommended after ~%d more min of study." % int(remaining)
