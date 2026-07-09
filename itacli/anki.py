"""Anki bridge (SPECS §4, §7-vocab).

All cards live in Anki. This talks to the AnkiConnect add-on over HTTP using
only the standard library (no pip install). AnkiConnect must be installed in
Anki (add-on code 2055492159) and Anki must be running.

  push: add_card()  -> create a Basic note
  pull: review_stats() -> per-card review history (feeds the Proficiency score)
"""
import json
import urllib.error
import urllib.request

from . import db

TIMEOUT = 4  # seconds


class AnkiUnavailable(RuntimeError):
    """Raised when Anki / AnkiConnect can't be reached."""


def _endpoint():
    return db.get_setting("ankiconnect_url", "http://127.0.0.1:8765")


def _invoke(action, **params):
    payload = json.dumps({"action": action, "version": 6, "params": params}).encode()
    req = urllib.request.Request(
        _endpoint(), data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            body = json.loads(resp.read().decode())
    except (urllib.error.URLError, OSError) as e:
        raise AnkiUnavailable(
            "Could not reach AnkiConnect at %s. Is Anki open with the "
            "AnkiConnect add-on installed?" % _endpoint()
        ) from e
    if body.get("error"):
        raise RuntimeError("AnkiConnect error: %s" % body["error"])
    return body.get("result")


def is_available():
    try:
        _invoke("version")
        return True
    except (AnkiUnavailable, RuntimeError):
        return False


def ensure_deck(deck):
    _invoke("createDeck", deck=deck)


def add_card(front, back="", deck=None, tags=("itacli",)):
    """Create a Basic note. Returns the new note id.

    Duplicates are allowed to fail softly (returns None) so the capture
    pipeline can keep going.
    """
    deck = deck or db.get_setting("anki_deck", "itacli")
    ensure_deck(deck)
    note = {
        "deckName": deck,
        "modelName": "Basic",
        "fields": {"Front": front, "Back": back},
        "tags": list(tags),
        "options": {"allowDuplicate": False},
    }
    try:
        return _invoke("addNote", note=note)
    except RuntimeError:
        return None  # duplicate or model issue; caller can inspect separately


def review_stats(query="tag:itacli"):
    """Return per-card review info for the Proficiency score. Best-effort."""
    card_ids = _invoke("findCards", query=query)
    if not card_ids:
        return []
    return _invoke("cardsInfo", cards=card_ids)
