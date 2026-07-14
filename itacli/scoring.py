"""Scoring engines (SPECS §8). Deterministic, always-on Proficiency score -
INDEPENDENT of the discrete CEFR assessment (§9, assessment.py).

Beta blend of the signals we actually have: recent exercise accuracy, vocab
breadth, and Anki retention when reachable. Anchored to the last CEFR
assessment band when one exists. Rendered as the home thermometer. No AI.
"""
from . import anki, concepts, db

BANDS = ["A1", "A2", "B1", "B2", "C1", "C2"]
VOCAB_TARGET = 150          # words that count as "full" breadth for the beta
RECENT = 60                 # attempts window


def _level_accuracy(level):
    """Accuracy on graded items whose grammar concept sits at `level`.
    Returns (accuracy, total) or None if nothing attempted at that level."""
    keys = [c["key"] for c in concepts.CATALOG if c["cefr"] == level]
    if not keys:
        return None
    tags = ["grammar:" + k for k in keys]
    conn = db.connect()
    try:
        placeholders = ",".join("?" * len(tags))
        total, correct = conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(correct), 0) FROM attempts "
            "WHERE concept_tags IN (%s)" % placeholders, tags).fetchone()
    finally:
        conn.close()
    if not total:
        return None
    return correct / total, total


def _recent_accuracy():
    conn = db.connect()
    try:
        rows = conn.execute(
            "SELECT correct FROM attempts ORDER BY id DESC LIMIT ?", (RECENT,)
        ).fetchall()
    finally:
        conn.close()
    if not rows:
        return None
    return sum(r[0] for r in rows) / len(rows)


def _vocab_breadth():
    conn = db.connect()
    try:
        n = conn.execute("SELECT COUNT(*) FROM vocab").fetchone()[0]
    finally:
        conn.close()
    return min(1.0, n / VOCAB_TARGET)


def _anki_retention():
    """Fraction of reviewed itacli cards not lapsing. None if Anki is down."""
    try:
        cards = anki.review_stats()
    except Exception:
        return None
    reviewed = [c for c in cards if c.get("reps")]
    if not reviewed:
        return None
    return sum(1 - c.get("lapses", 0) / (c["reps"] + c.get("lapses", 0) + 1)
               for c in reviewed) / len(reviewed)


def _last_band():
    conn = db.connect()
    try:
        row = conn.execute(
            "SELECT cefr_overall FROM assessments ORDER BY id DESC LIMIT 1"
        ).fetchone()
    finally:
        conn.close()
    return row[0] if row and row[0] in BANDS else None


def proficiency_beta():
    """Return (fraction_0_1, label, has_data). INTER-LEVEL: the fraction is how
    far you are from your current CEFR band to the NEXT one, measured by your
    accuracy on next-band material. Falls back to a competence blend only when
    there's no CEFR band yet.
    """
    band = _last_band()

    if not band:                       # no assessment yet -> uncalibrated blend
        acc = _recent_accuracy()
        breadth = _vocab_breadth()
        if acc is None and breadth == 0.0:
            return 0.0, "no data yet", False
        parts = [(acc, 0.6), (breadth, 0.4)] if acc is not None else [(breadth, 1.0)]
        fraction = sum(p * w for p, w in parts) / sum(w for _, w in parts)
        fraction = max(0.0, min(1.0, fraction))
        return fraction, "%d%% · uncalibrated" % round(fraction * 100), True

    i = BANDS.index(band)
    if i >= len(BANDS) - 1:
        return 1.0, "C2 - top level", True

    nxt = BANDS[i + 1]
    la = _level_accuracy(nxt)          # accuracy on next-band items
    if la is None:
        return 0.0, "toward %s" % nxt, True
    fraction, _ = la
    return max(0.0, min(1.0, fraction)), "%d%% toward %s" % (round(fraction * 100), nxt), True
