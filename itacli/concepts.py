"""Grammar-concept catalogue + per-concept mastery (SPECS §7-grammar, §Progress).

A background map of the grammatical concepts that matter for CEFR, plus the
user's progress on each - computed from the `attempts` log (every grammar drill
and CEFR grammar item is tagged with a concept). Drives 'repeat until mastery'
(grammar picks weak concepts first) and the Progress screen.
"""
from . import db

# Concept catalogue, ordered by CEFR level. `key` is what attempts are tagged
# with (as 'grammar:<key>').
CATALOG = [
    {"key": "articles", "name": "Articles (il/lo/la...)", "cefr": "A1"},
    {"key": "noun-plural", "name": "Noun plurals", "cefr": "A1"},
    {"key": "present-tense", "name": "Present tense", "cefr": "A1"},
    {"key": "passato-prossimo", "name": "Passato prossimo", "cefr": "A2"},
    {"key": "prepositions", "name": "Prepositions", "cefr": "A2"},
    {"key": "comparatives", "name": "Comparatives", "cefr": "A2"},
    {"key": "imperfetto", "name": "Imperfetto", "cefr": "B1"},
    {"key": "pronouns", "name": "Object pronouns", "cefr": "B1"},
    {"key": "congiuntivo", "name": "Congiuntivo (present)", "cefr": "B1"},
    {"key": "conditional", "name": "Conditional", "cefr": "B1"},
    {"key": "passive", "name": "Passive voice", "cefr": "B2"},
    {"key": "congiuntivo-imperfetto", "name": "Congiuntivo imperfetto", "cefr": "B2"},
]

# Template/assessment concept strings that map onto a catalogue key.
ALIAS = {
    "definite-article": "articles",
    "indefinite-article": "articles",
}

MASTERED_MIN = 4        # need at least this many attempts
MASTERED_ACC = 0.8      # and this accuracy to count as mastered


def normalize(tag):
    """'grammar:definite-article' / 'definite-article' -> catalogue key."""
    key = tag.split(":")[-1] if ":" in tag else tag
    return ALIAS.get(key, key)


def _status(total, correct):
    if total == 0:
        return "not started"
    acc = correct / total
    if total >= MASTERED_MIN and acc >= MASTERED_ACC:
        return "mastered"
    return "learning"


def mastery():
    """Per-concept progress: list of dicts with total/correct/accuracy/status."""
    conn = db.connect()
    try:
        rows = conn.execute(
            "SELECT concept_tags, correct FROM attempts "
            "WHERE concept_tags LIKE 'grammar:%'"
        ).fetchall()
    finally:
        conn.close()
    agg = {}
    for tag, correct in rows:
        key = normalize(tag)
        t, c = agg.get(key, (0, 0))
        agg[key] = (t + 1, c + (correct or 0))
    out = []
    for concept in CATALOG:
        t, c = agg.get(concept["key"], (0, 0))
        out.append({
            "key": concept["key"], "name": concept["name"], "cefr": concept["cefr"],
            "total": t, "correct": c,
            "accuracy": (c / t) if t else None,
            "status": _status(t, c),
        })
    return out


def weak_keys():
    """Concept keys that are not yet mastered (learning or unseen), weakest
    first - used to repeat what the user struggles with."""
    m = mastery()
    seen = [x for x in m if x["total"] > 0 and x["status"] != "mastered"]
    seen.sort(key=lambda x: x["accuracy"])
    unseen = [x for x in m if x["total"] == 0]
    return [x["key"] for x in seen] + [x["key"] for x in unseen]
