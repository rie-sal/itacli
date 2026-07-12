"""Adaptive daily session (SPECS §6 'Daily session', the engine that mixes
activities by weak spots + time budget). Deterministic. Beta.

build_plan() is cheap (a couple of queries) so the home screen can show today's
mix; open_daily() runs the activities in sequence.
"""
from . import db, study, ui

GRAMMAR_HINTS = ("grammar", "article", "plural", "present", "tense",
                 "congiuntivo", "prepos")


def _weak_concepts():
    conn = db.connect()
    try:
        rows = conn.execute(
            "SELECT concept_tags FROM attempts WHERE concept_tags IS NOT NULL "
            "GROUP BY concept_tags HAVING SUM(CASE WHEN correct=0 THEN 1 ELSE 0 END) > 0"
        ).fetchall()
    finally:
        conn.close()
    return [r[0].lower() for r in rows]


def _grammar_unlocked():
    from . import grammar
    return len(grammar._usable_items()) >= grammar.MIN_TAGGED


def build_plan():
    """Return [(activity, minutes), ...] adapted to weaknesses + time budget."""
    budget = int(float(db.get_setting("time_budget_min", "30")))
    weights = {"Reading": 0.4, "Vocabulary review": 0.2}
    if _grammar_unlocked():
        weights["Grammar"] = 0.4
    else:
        weights["Reading"] += 0.4          # grammar locked -> read more

    # weakness boost: if the weak concepts look grammatical, favour grammar
    weak = _weak_concepts()
    if "Grammar" in weights and any(
            any(h in w for h in GRAMMAR_HINTS) for w in weak):
        shift = min(0.15, weights["Reading"] - 0.1)
        weights["Grammar"] += shift
        weights["Reading"] -= shift

    if study.assessment_due():
        weights["CEFR check"] = 0.15

    total = sum(weights.values())
    order = ["Grammar", "Reading", "Vocabulary review", "CEFR check"]
    plan = []
    for name in order:
        if name in weights:
            plan.append((name, max(1, round(weights[name] / total * budget))))
    return plan


def _run_activity(name):
    if name == "Reading":
        from . import reading
        reading.open_reading()
    elif name == "Grammar":
        from . import grammar
        grammar.open_grammar()
    elif name == "CEFR check":
        from . import assessment
        assessment.open_assessment()
    elif name == "Vocabulary review":
        from . import anki
        up = anki.is_available()
        ui.panel("Vocabulary review", [
            "Review your due cards in Anki.",
            "Anki is %s." % ("open - go review!" if up
                             else "not running - open it to review."),
        ])


def open_daily():
    plan = build_plan()
    ui.clear()
    ui.blank()
    ui.two_sided("Daily session", "%d min budget" % int(float(
        db.get_setting("time_budget_min", "30"))))
    ui.blank()
    ui.rule()
    ui.blank()
    ui.line("Today's mix (adapts to what you struggle with):")
    ui.blank()
    for name, mins in plan:
        ui.line("  %-20s %d min" % (name, mins))
    ui.blank()
    ui.rule()
    ui.line("[Enter] start each in turn  ·  [q] back")
    ui.blank()
    try:
        if input(ui.INDENT + "> ").strip().lower() == "q":
            return
    except EOFError:
        return

    for name, mins in plan:
        ui.clear()
        ui.blank()
        ui.line("Next: %s  (~%d min)" % (name, mins))
        ui.blank()
        try:
            choice = input(ui.INDENT + "[Enter] start · [s] skip · [q] quit: ").strip().lower()
        except EOFError:
            return
        if choice == "q":
            return
        if choice == "s":
            continue
        _run_activity(name)

    ui.panel("Daily session - done", ["Bel lavoro! That's today's mix complete."])
