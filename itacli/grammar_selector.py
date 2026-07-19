"""Grammar question SELECTION algorithm (SPECS §7-grammar).

This is the brain that decides which grammar exercises to show, so the app
constantly challenges you: drill what you struggle with, retire what you've
mastered, reproduce the exact verb+tense combos you looked up, and keep a mix of
concepts and new/review material.

SIGNALS & PRIORITY (highest first):
  1. Concept mastery (concepts.py, from the attempts log): a MASTERED concept is
     removed entirely (score 0); a LEARNING concept gets the most weight; a
     NOT-STARTED concept gets medium weight (so new concepts still get shown).
  2. Highlighted verb-tense tally: tenses you highlighted while reading (stored
     on each captured verb) are boosted - the more you looked up a tense, the
     more it appears (until its concept is mastered, per signal 1).
  3. Highlighted verb->tense pairs: the exact (verb, tense) you looked up is
     reproduced more often - same verb, same tense.
  4. Anki card mastery: if the word's Anki card is mature/mastered it's shown
     less; if you're still learning it, it's shown more. (Needs Anki reachable;
     skipped otherwise.)
  5. New over review: NEW concepts outweigh ones you've largely learned; only
     genuinely weak concepts beat new content. Spaced repetition rests a concept
     you just got right. Selection is by need (NOT forced variety - a concept you
     really need can dominate), jittered, then ordered easiest-CEFR-first so each
     session ramps up in difficulty.

WHERE IT LIVES: this module (itacli/grammar_selector.py). grammar.open_grammar()
calls select(). Weights are the module constants below - tune them there.
"""
import random

from . import concepts, db, morph, templates

W_NEW = 3.0             # weight for a not-started concept (favour new content)
TENSE_TALLY_BOOST = 0.6  # per highlight of that tense
VERB_TENSE_PAIR_BOOST = 2.0  # exact (verb, tense) you looked up
ANKI_MASTERED_FACTOR = 0.35  # show mastered-card words this much as often


def _usable_vocab():
    conn = db.connect()
    try:
        rows = conn.execute(
            "SELECT term, pos, gender, lemma, features FROM vocab "
            "WHERE (pos='noun' AND gender IN ('m','f')) OR pos='verb'").fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def _tense_tally():
    conn = db.connect()
    try:
        rows = conn.execute(
            "SELECT features, COUNT(*) FROM vocab "
            "WHERE pos='verb' AND features IS NOT NULL GROUP BY features").fetchall()
    finally:
        conn.close()
    return {r[0]: r[1] for r in rows}


def _verb_tense_pairs():
    conn = db.connect()
    try:
        rows = conn.execute(
            "SELECT lower(lemma), features FROM vocab "
            "WHERE pos='verb' AND features IS NOT NULL AND lemma IS NOT NULL").fetchall()
    finally:
        conn.close()
    return set((r[0], r[1]) for r in rows)


def _anki_mastered_terms():
    from . import anki
    try:
        cards = anki.review_stats()
    except Exception:
        return set()
    notes = {c.get("note") for c in cards
             if c.get("interval", 0) >= 21 and c.get("reps", 0) >= 3}
    notes.discard(None)
    if not notes:
        return set()
    conn = db.connect()
    try:
        q = ("SELECT lower(term) FROM vocab WHERE anki_note_id IN (%s)"
             % ",".join("?" * len(notes)))
        rows = conn.execute(q, tuple(notes)).fetchall()
    finally:
        conn.close()
    return {r[0] for r in rows}


def _candidates(vocab):
    """Every exercise the current vocab can produce (noun drills + verb tenses)."""
    out = []
    for it in vocab:
        if it["pos"] == "noun" and it["gender"] in ("m", "f"):
            for t in templates.buildable(it):
                ex = t.build(it)
                if ex:
                    out.append({"exercise": ex, "concept": ex["concept"],
                                "word": it["term"].lower(), "tense": None})
        elif it["pos"] == "verb":
            lemma = (it.get("lemma") or it["term"]).lower()
            for concept in morph.VERB_TENSE:
                ex = templates.verb_exercise(it, concept)
                if ex:
                    out.append({"exercise": ex, "concept": concept,
                                "word": lemma, "tense": concept})
    return out


def _recent_correct_concepts(n=8):
    """Concepts answered correctly in the last n attempts - rested a bit so they
    space out (spaced repetition), without blocking genuinely weak ones."""
    conn = db.connect()
    try:
        rows = conn.execute(
            "SELECT concept_tags FROM attempts WHERE correct=1 AND "
            "concept_tags LIKE 'grammar:%' ORDER BY id DESC LIMIT ?", (n,)).fetchall()
    finally:
        conn.close()
    return {concepts.normalize(r[0]) for r in rows}


def _score(c, mastery, tally, pairs, anki_mastered, recent_ok):
    key = concepts.normalize(c["concept"])
    m = mastery.get(key)
    if m and m["status"] == "mastered":
        return 0.0                                   # (1) mastered -> removed
    if m and m["status"] == "learning":
        # weaker -> higher; a nearly-mastered concept dips BELOW new content
        base = 1.5 + 3.0 * (1.0 - (m["accuracy"] or 0.0))
    else:
        base = W_NEW                                 # (1b) favour new content
    if c["tense"]:                                   # (2) tense tally
        base *= 1.0 + TENSE_TALLY_BOOST * tally.get(c["tense"], 0)
    if c["tense"] and (c["word"], c["tense"]) in pairs:   # (3) exact combo
        base *= VERB_TENSE_PAIR_BOOST
    if c["word"] in anki_mastered:                   # (4) mastered card -> less
        base *= ANKI_MASTERED_FACTOR
    if key in recent_ok:                             # (1c) spaced repetition
        base *= 0.5
    return base


# concepts.CATALOG is CEFR-ordered, so this gives an easy->hard difficulty ramp.
_CEFR_RANK = {c["key"]: i for i, c in enumerate(concepts.CATALOG)}


def select(n=8):
    """Return up to n exercise dicts. Ranked purely by weakness/need (no forced
    variety - if one concept dominates, so be it), jittered, then ordered easiest
    CEFR first so each session ramps up."""
    vocab = _usable_vocab()
    if not vocab:
        return []
    mastery = {m["key"]: m for m in concepts.mastery()}
    tally, pairs, anki_m = _tense_tally(), _verb_tense_pairs(), _anki_mastered_terms()
    recent_ok = _recent_correct_concepts()

    scored = []
    for c in _candidates(vocab):
        s = _score(c, mastery, tally, pairs, anki_m, recent_ok)
        if s > 0:
            scored.append((c, s * random.uniform(0.8, 1.2)))    # light jitter only
    scored.sort(key=lambda cs: cs[1], reverse=True)
    chosen = [c for c, _ in scored[:n]]
    chosen.sort(key=lambda c: _CEFR_RANK.get(concepts.normalize(c["concept"]), 99))
    return [c["exercise"] for c in chosen]
