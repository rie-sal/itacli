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


def translate(text, target="en"):
    """Translate via Apple's on-device translation (a macOS Shortcut).

    target='en' uses the 'itacli Translate' shortcut (Italian->English);
    target='it' uses 'itacli Translate to Italian' (English->Italian) so the
    user can also highlight native-language words. Returns "" if the relevant
    shortcut isn't installed. No LLM, no network.
    """
    key = "translate_shortcut" if target == "en" else "translate_it_shortcut"
    name = db.get_setting(key, "")
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


# A few very common English words - used only to guess if the SELECTION is in
# the user's native language (so we can translate the other way).
_EN_COMMON = set((
    "the of and to a in is it you that he was for on are with as his they be at "
    "this from or by but not what all we when can there an which do how if").split())


def _looks_english(text):
    from . import sources
    words = [w.strip(".,;:!?\"'()[]").lower() for w in text.split()]
    words = [w for w in words if w.isalpha()]
    if not words:
        return False
    en = sum(1 for w in words if w in _EN_COMMON) / len(words)
    return en > sources.italian_ratio(text) and en > 0.1


def _canonical(term):
    """Return (italian_form, pos, gender, tense_concept). A single Italian word
    becomes its LEMMA (un-conjugated: 'vado'->'andare', 'gatti'->'gatto');
    phrases stay as-is."""
    from . import morph
    if " " in term.strip() or not term.strip().isalpha():
        return term.strip(), None, None, None
    pos, gender, lemma = morph.analyze(term)
    tense = morph.verb_concept(term) if pos == "verb" else None
    return (lemma or term.strip().lower()), pos, gender, tense


def _already_have(italian):
    conn = db.connect()
    try:
        row = conn.execute(
            "SELECT 1 FROM vocab WHERE lower(term)=lower(?) OR lower(lemma)=lower(?)",
            (italian, italian)).fetchone()
        return row is not None
    finally:
        conn.close()


def _save_vocab(italian, english, pos, gender, tense, context, anki_id):
    conn = db.connect()
    try:
        conn.execute(
            "INSERT INTO vocab(term, gloss, source_context, status, "
            "anki_note_id, added_from, pos, gender, lemma, features) "
            "VALUES (?, ?, ?, 'new', ?, 'capture', ?, ?, ?, ?)",
            (italian, english, context, anki_id, pos, gender, italian, tense),
        )
        conn.commit()
    finally:
        conn.close()


def capture_pipeline(text, notify=False):
    """Capture -> chunk -> canonicalise (un-conjugate) -> dedupe -> translate ->
    save a card (FRONT = Italian, BACK = English). Works whether the selection
    is Italian or the user's native language. notify=True shows a popup (real
    capture only; tests pass False)."""
    text = (text or "").strip()
    if not text:
        return {"captured": "", "added": [], "skipped": [], "note": "empty selection"}

    native = _looks_english(text)
    added, skipped, seen = [], [], set()
    anki_up = anki.is_available()
    for term in chunk(text):
        if native:                          # user highlighted English -> get Italian
            italian = translate(term, target="it")
            if not italian:
                continue                    # need the reverse shortcut; skip quietly
            it_form, pos, gender, tense = _canonical(italian)
            english = term
        else:
            it_form, pos, gender, tense = _canonical(term)
            english = translate(it_form, target="en")
        if it_form.lower() in seen or _already_have(it_form):
            continue
        seen.add(it_form.lower())
        note_id = anki.add_card(it_form, english) if anki_up else None   # front=IT, back=EN
        _save_vocab(it_form, english, pos, gender, tense, text, note_id)
        (added if note_id or not anki_up else skipped).append(it_form)
    if notify and db.get_setting("show_popup", "1") == "1":
        _show_translation_popup(text)
    return {
        "captured": text,
        "added": added,
        "skipped": skipped,
        "anki": anki_up,
    }


def _notify(title, message):
    """Show a floating macOS dialog (auto-dismisses) with the translation."""
    t = message.replace('"', "'")
    ti = title.replace('"', "'")
    _run(["osascript", "-e",
          'display dialog "%s" with title "%s" buttons {"OK"} '
          'default button "OK" giving up after 8 with icon note' % (t, ti)])


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
