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
  5. Variety: never repeat a concept back-to-back; scores are jittered so the
     set isn't identical each time - a mix of concepts and new vs review.

WHERE IT LIVES: this module (itacli/grammar_selector.py). grammar.open_grammar()
calls select(). Weights are the module constants below - tune them there.
"""
import random

from . import concepts, db, morph, templates

W_LEARNING = 3.0        # weight for a concept you're actively learning
W_NEW = 2.0             # weight for a concept not started yet (introduce it)
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


def _score(c, mastery, tally, pairs, anki_mastered):
    key = concepts.normalize(c["concept"])
    m = mastery.get(key)
    if m and m["status"] == "mastered":
        return 0.0                                   # (1) mastered -> removed
    base = W_LEARNING if (m and m["status"] == "learning") else W_NEW
    if c["tense"]:                                   # (2) tense tally
        base *= 1.0 + TENSE_TALLY_BOOST * tally.get(c["tense"], 0)
    if c["tense"] and (c["word"], c["tense"]) in pairs:   # (3) exact combo
        base *= VERB_TENSE_PAIR_BOOST
    if c["word"] in anki_mastered:                   # (4) mastered card -> less
        base *= ANKI_MASTERED_FACTOR
    return base


def select(n=8):
    """Return up to n exercise dicts, ranked + varied per the algorithm above."""
    vocab = _usable_vocab()
    if not vocab:
        return []
    mastery = {m["key"]: m for m in concepts.mastery()}
    tally, pairs, anki_m = _tense_tally(), _verb_tense_pairs(), _anki_mastered_terms()

    scored = []
    for c in _candidates(vocab):
        s = _score(c, mastery, tally, pairs, anki_m)
        if s > 0:
            scored.append((c, s * random.uniform(0.85, 1.15)))   # (5) jitter
    scored.sort(key=lambda cs: cs[1], reverse=True)

    chosen, last = [], None                          # (5) no concept twice in a row
    pool = scored[:]
    while pool and len(chosen) < n:
        idx = next((i for i, (c, _) in enumerate(pool) if c["concept"] != last), 0)
        c, _ = pool.pop(idx)
        chosen.append(c["exercise"])
        last = c["concept"]
    return chosen
