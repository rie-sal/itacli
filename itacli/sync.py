"""Offline pending-sync queue (SPECS §5, §10).

itacli is offline-first: capture/reading save vocab to the local DB even when
Anki is closed or there's no network. Any card that couldn't be pushed yet is
simply a vocab row with anki_note_id IS NULL - that's the queue. flush() pushes
them the moment Anki is reachable again, and runs automatically at startup.
"""
from . import anki, capture, db


def pending_count():
    conn = db.connect()
    try:
        return conn.execute(
            "SELECT COUNT(*) FROM vocab WHERE anki_note_id IS NULL"
        ).fetchone()[0]
    finally:
        conn.close()


def flush(limit=200):
    """Push queued vocab to Anki if it's reachable. Returns count pushed."""
    if pending_count() == 0 or not anki.is_available():
        return 0
    conn = db.connect()
    try:
        rows = conn.execute(
            "SELECT id, term, gloss FROM vocab WHERE anki_note_id IS NULL LIMIT ?",
            (limit,),
        ).fetchall()
    finally:
        conn.close()
    pushed = 0
    for row in rows:
        back = row["gloss"] or capture.translate(row["term"])
        note_id = anki.add_card(row["term"], back)
        if note_id:
            conn2 = db.connect()
            try:
                conn2.execute(
                    "UPDATE vocab SET anki_note_id = ?, gloss = ? WHERE id = ?",
                    (note_id, back, row["id"]),
                )
                conn2.commit()
            finally:
                conn2.close()
            pushed += 1
    return pushed
