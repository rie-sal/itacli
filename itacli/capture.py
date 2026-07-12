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
import os
import subprocess
import sys
import tempfile

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


_shortcuts_cache = None


def _installed_shortcuts():
    """Names of the user's macOS Shortcuts (cached per process)."""
    global _shortcuts_cache
    if _shortcuts_cache is None:
        res = _run(["shortcuts", "list"])
        _shortcuts_cache = (
            set(l.strip() for l in res.stdout.splitlines() if l.strip())
            if res and res.returncode == 0 else set()
        )
    return _shortcuts_cache


def translate(text):
    """Gloss via Apple's on-device translation, run through a macOS Shortcut.

    Uses file I/O (--input-path/--output-path) for reliability. Returns "" if
    the Shortcut isn't installed yet, so the card is still created and you can
    add the meaning in Anki. No LLM, no network.
    """
    name = db.get_setting("translate_shortcut", "")
    if not name or name not in _installed_shortcuts():
        return ""
    try:
        with tempfile.TemporaryDirectory() as d:
            fin, fout = os.path.join(d, "in.txt"), os.path.join(d, "out.txt")
            with open(fin, "w", encoding="utf-8") as f:
                f.write(text)
            res = _run(["shortcuts", "run", name,
                        "--input-path", fin, "--output-path", fout])
            if res and res.returncode == 0 and os.path.exists(fout):
                with open(fout, encoding="utf-8") as f:
                    return f.read().strip()
    except OSError:
        pass
    return ""


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
        _SPACY = spacy.load("it_core_news_md")
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
    from . import morph
    pos, gender, lemma = morph.analyze(term)
    conn = db.connect()
    try:
        conn.execute(
            "INSERT INTO vocab(term, gloss, source_context, status, "
            "anki_note_id, added_from, pos, gender, lemma) "
            "VALUES (?, ?, ?, 'new', ?, 'capture', ?, ?, ?)",
            (term, gloss, context, anki_id, pos, gender, lemma),
        )
        conn.commit()
    finally:
        conn.close()


def capture_pipeline(text, notify=False):
    """Run the full pipeline on already-captured text. Returns a summary dict.

    notify=True shows a translation popup (real capture only; tests pass False
    so no GUI fires)."""
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
    if notify and db.get_setting("show_popup", "1") == "1":
        _show_translation_popup(text)
    return {
        "captured": text,
        "added": added,
        "skipped": skipped,
        "anki": anki_up,
    }


def _notify(title, message):
    """Show a macOS notification popup."""
    t = message.replace('"', "'")
    ti = title.replace('"', "'")
    _run(["osascript", "-e",
          'display notification "%s" with title "%s"' % (t, ti)])


def _show_translation_popup(text):
    """The 'translate popup': show the selection's translation (Apple engine)."""
    trans = translate(text)
    if trans:
        snippet = text if len(text) <= 40 else text[:37] + "..."
        _notify("itacli · translation", "%s → %s" % (snippet, trans))


def capture_once():
    """One capture cycle (entry point for `run.py capture` / an OS binding)."""
    text = read_selection()
    result = capture_pipeline(text, notify=True)
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
        _report(capture_pipeline(read_selection(), notify=True))

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
