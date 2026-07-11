"""CEFR assessment (SPECS §9): closed-form, auto-graded, no speaking.

Administers CEFR-tagged items level by level and estimates a band as the
highest contiguous level the user passes. Directional but honest. Separate
from the continuous Proficiency score (§8). Spaced by time studied (study.py),
but always available on demand.
"""
import datetime
import random

from . import assessment_items as bank
from . import db, study, ui

PASS = 0.6   # fraction correct to "pass" a level


def _ask(item, index, total):
    choices = list(item["choices"])
    random.shuffle(choices)   # so the answer isn't always in the same slot
    ui.clear()
    ui.blank()
    ui.two_sided("CEFR assessment", "%d / %d" % (index, total))
    ui.blank()
    ui.rule()
    ui.blank()
    ui.line(item["q"])
    ui.blank()
    for i, choice in enumerate(choices, start=1):
        ui.line("  %d  %s" % (i, choice))
    ui.blank()
    try:
        raw = input(ui.INDENT + "  answer (number, or q to stop): ").strip().lower()
    except EOFError:
        return None
    if raw in ("q", "quit"):
        return None
    if raw.isdigit() and 1 <= int(raw) <= len(choices):
        return choices[int(raw) - 1] == item["answer"]
    return False   # unparseable = wrong


def _estimate(level_scores):
    """Highest contiguous level with accuracy >= PASS. None if A1 not passed."""
    passed = None
    for lvl in bank.LEVELS:
        total, correct = level_scores.get(lvl, (0, 0))
        if total and correct / total >= PASS:
            passed = lvl
        else:
            break
    return passed


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
    level_scores = {lvl: [0, 0] for lvl in bank.LEVELS}      # [total, correct]
    skill_scores = {}
    asked_ids = []

    for idx, item in enumerate(items, start=1):
        result = _ask(item, idx, len(items))
        if result is None:
            ui.panel("CEFR assessment", ["Stopped early - no score recorded.",
                                         "Run it again when you have a few minutes."])
            return
        asked_ids.append(item["id"])
        level_scores[item["cefr"]][0] += 1
        level_scores[item["cefr"]][1] += int(result)
        s = skill_scores.setdefault(item["skill"], [0, 0])
        s[0] += 1
        s[1] += int(result)

    ls = {lvl: (t, c) for lvl, (t, c) in level_scores.items()}
    overall = _estimate(ls) or "pre-A1"
    per_skill = {}
    for skill, (t, c) in skill_scores.items():
        per_skill[skill] = _estimate_from_ratio(skill, ls, overall)
    _store(overall if overall != "pre-A1" else "A1<", per_skill, asked_ids)

    lines = ["Your estimated CEFR level:  %s" % overall, ""]
    for lvl in bank.LEVELS:
        t, c = ls[lvl]
        if t:
            lines.append("  %s   %d / %d correct" % (lvl, c, t))
    lines += ["", "This is a directional estimate from closed-form items -",
              "no speaking. It updates each time you take it."]
    ui.panel("CEFR assessment - done", lines)


def _estimate_from_ratio(skill, level_scores, overall):
    """Per-skill band: reuse the overall estimate for now (beta)."""
    return overall if overall != "pre-A1" else "A1<"


def cadence_note():
    if study.assessment_due():
        return "A CEFR check is recommended now (you've studied enough since the last)."
    remaining = study.ASSESS_EVERY_MIN - study.minutes_since_last_assessment()
    return "Next CEFR check recommended after ~%d more min of study." % int(remaining)
