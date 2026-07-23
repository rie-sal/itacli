"""Grammar-concept catalogue + per-concept mastery (SPECS §7-grammar, §Progress).

A background map of the grammatical concepts that matter for CEFR, plus the
user's progress on each - computed from the `attempts` log (every grammar drill
and CEFR grammar item is tagged with a concept). Drives 'repeat until mastery'
(grammar picks weak concepts first) and the Progress screen.
"""
from . import db

# Concept catalogue, CEFR-mapped (loosely after the Profilo della lingua
# italiana / common Italian syllabi), ordered easy->hard. `key` is what attempts
# are tagged with (as 'grammar:<key>'). `gen` marks how it's DRILLABLE today:
#   'articles'/'plural' = built-in rule frames; 'verb' = mlconjug3 tense frames
#   (morph.VERB_TENSE); None = tracked (from assessment) but no generator yet -
#   these need an authored fill-in frame, added over time.
CATALOG = [
    # ---- A1 ----
    {"key": "articles", "name": "Articles (il/lo/la...)", "cefr": "A1", "gen": "articles"},
    {"key": "noun-gender", "name": "Noun gender", "cefr": "A1", "gen": None},
    {"key": "noun-plural", "name": "Noun plurals", "cefr": "A1", "gen": "plural"},
    {"key": "adjective-agreement", "name": "Adjective agreement", "cefr": "A1", "gen": None},
    {"key": "subject-pronouns", "name": "Subject pronouns", "cefr": "A1", "gen": None},
    {"key": "essere-avere", "name": "essere & avere (present)", "cefr": "A1", "gen": None},
    {"key": "present-tense", "name": "Present tense", "cefr": "A1", "gen": "verb"},
    {"key": "demonstratives", "name": "Demonstratives (questo/quello)", "cefr": "A1", "gen": None},
    {"key": "possessives", "name": "Possessives (mio/tuo...)", "cefr": "A1", "gen": None},
    {"key": "c-e-ci-sono", "name": "c'e / ci sono", "cefr": "A1", "gen": None},
    {"key": "prepositions", "name": "Simple prepositions (a/in/di/da)", "cefr": "A1", "gen": None},
    # ---- A2 ----
    {"key": "articulated-prepositions", "name": "Articulated prepositions (del/nel/sul)", "cefr": "A2", "gen": None},
    {"key": "passato-prossimo", "name": "Passato prossimo", "cefr": "A2", "gen": "verb"},
    {"key": "imperfetto", "name": "Imperfetto", "cefr": "A2", "gen": "verb"},
    {"key": "futuro", "name": "Future tense", "cefr": "A2", "gen": "verb"},
    {"key": "reflexive-verbs", "name": "Reflexive verbs", "cefr": "A2", "gen": None},
    {"key": "direct-pronouns", "name": "Direct object pronouns (lo/la/li/le)", "cefr": "A2", "gen": None},
    {"key": "indirect-pronouns", "name": "Indirect object pronouns (gli/le)", "cefr": "A2", "gen": None},
    {"key": "modal-verbs", "name": "Modal verbs (potere/dovere/volere)", "cefr": "A2", "gen": None},
    {"key": "comparatives", "name": "Comparatives", "cefr": "A2", "gen": None},
    {"key": "superlatives", "name": "Superlatives", "cefr": "A2", "gen": None},
    {"key": "ci-ne", "name": "Particles ci / ne", "cefr": "A2", "gen": None},
    {"key": "imperativo", "name": "Imperative (informal)", "cefr": "A2", "gen": None},
    {"key": "gerundio-progressive", "name": "stare + gerundio (continuous)", "cefr": "A2", "gen": None},
    # ---- B1 ----
    {"key": "pronouns", "name": "Object pronouns (review)", "cefr": "B1", "gen": None},
    {"key": "combined-pronouns", "name": "Combined pronouns (glielo)", "cefr": "B1", "gen": None},
    {"key": "aspect-imperfetto-pp", "name": "Imperfetto vs passato prossimo", "cefr": "B1", "gen": None},
    {"key": "congiuntivo", "name": "Congiuntivo (present)", "cefr": "B1", "gen": "verb"},
    {"key": "conditional", "name": "Conditional (present)", "cefr": "B1", "gen": "verb"},
    {"key": "relative-pronouns", "name": "Relative pronouns (che/cui)", "cefr": "B1", "gen": None},
    {"key": "si-impersonale", "name": "si impersonale", "cefr": "B1", "gen": None},
    {"key": "imperativo-formal", "name": "Imperative (formal Lei)", "cefr": "B1", "gen": None},
    {"key": "periodo-ipotetico-1", "name": "Hypothetical (real / type 1)", "cefr": "B1", "gen": None},
    # ---- B2 ----
    {"key": "congiuntivo-imperfetto", "name": "Congiuntivo imperfetto", "cefr": "B2", "gen": "verb"},
    {"key": "congiuntivo-passato", "name": "Congiuntivo passato", "cefr": "B2", "gen": "verb"},
    {"key": "condizionale-passato", "name": "Condizionale passato", "cefr": "B2", "gen": "verb"},
    {"key": "passato-remoto", "name": "Passato remoto", "cefr": "B2", "gen": "verb"},
    {"key": "trapassato-prossimo", "name": "Trapassato prossimo", "cefr": "B2", "gen": "verb"},
    {"key": "passive", "name": "Passive voice (essere/venire)", "cefr": "B2", "gen": None},
    {"key": "si-passivante", "name": "si passivante", "cefr": "B2", "gen": None},
    {"key": "periodo-ipotetico-2", "name": "Hypothetical (unreal / type 2-3)", "cefr": "B2", "gen": None},
    {"key": "discorso-indiretto", "name": "Reported speech", "cefr": "B2", "gen": None},
    {"key": "concordanza-tempi", "name": "Sequence of tenses", "cefr": "B2", "gen": None},
    # ---- C1/C2 ----
    {"key": "congiuntivo-trapassato", "name": "Congiuntivo trapassato", "cefr": "C1", "gen": "verb"},
    {"key": "futuro-anteriore", "name": "Futuro anteriore", "cefr": "C1", "gen": "verb"},
    {"key": "causative", "name": "Causative (fare/lasciare + inf.)", "cefr": "C1", "gen": None},
    {"key": "gerundio-composto", "name": "Compound gerund / participle clauses", "cefr": "C2", "gen": None},
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
