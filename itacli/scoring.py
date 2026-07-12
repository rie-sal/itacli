"""Scoring engines (SPECS §8). Deterministic, always-on Proficiency score -
INDEPENDENT of the discrete CEFR assessment (§9, assessment.py).

Beta blend of the signals we actually have: recent exercise accuracy, vocab
breadth, and Anki retention when reachable. Anchored to the last CEFR
assessment band when one exists. Rendered as the home thermometer. No AI.
"""
from . import anki, db

BANDS = ["A1", "A2", "B1", "B2", "C1", "C2"]
VOCAB_TARGET = 150          # words that count as "full" breadth for the beta
RECENT = 60                 # attempts window


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
    """Return (fraction_0_1, label, has_data).

    fraction is 'progress toward the next band' when a CEFR band is known,
    else a raw competence blend. label is a short human string.
    """
    acc = _recent_accuracy()
    breadth = _vocab_breadth()
    retention = _anki_retention()

    if acc is None and breadth == 0.0:
        return 0.0, "no data yet - read or drill to build it", False

    parts, weights = [], []
    if acc is not None:
        parts.append(acc); weights.append(0.5)
    parts.append(breadth); weights.append(0.3)
    if retention is not None:
        parts.append(retention); weights.append(0.2)
    fraction = sum(p * w for p, w in zip(parts, weights)) / sum(weights)
    fraction = max(0.0, min(1.0, fraction))

    band = _last_band()
    if band:
        i = BANDS.index(band)
        nxt = BANDS[min(i + 1, len(BANDS) - 1)]
        label = "%d%% toward %s" % (round(fraction * 100), nxt)
    else:
        label = "%d%% (take a CEFR check to calibrate)" % round(fraction * 100)
    return fraction, label, True
