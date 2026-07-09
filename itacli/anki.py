"""Anki bridge (SPECS §4, §7-vocab). Stub.

All cards live in Anki. Two directions:
  - push: create notes (quick-add command; capture pipeline; reading queue).
  - pull: read review stats (retention, intervals, lapses, ease) to feed the
    Proficiency score.

Reachable via the AnkiConnect add-on over HTTP (localhost:8765, requires Anki
running) and/or the collection.anki2 SQLite DB. Getting deeply informed on
Anki internals is an explicit early task.
"""

ANKICONNECT_URL = "http://127.0.0.1:8765"


def add_card(front, back, deck="itacli", tags=("itacli",)):
    """Create a single note. Backs the quick-add command and capture."""
    # TODO: POST addNote to AnkiConnect.
    raise NotImplementedError


def review_stats():
    """Pull per-card review history for the Proficiency score."""
    # TODO: query AnkiConnect / collection DB.
    raise NotImplementedError
