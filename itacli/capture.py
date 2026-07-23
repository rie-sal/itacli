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
    import time
    before = _run(["pbpaste"])
    before = before.stdout if before and before.returncode == 0 else ""
    r = _run(["osascript", "-e",
              'tell application "System Events" to keystroke "c" using command down'])
    if r is None or r.returncode != 0:      # osascript blocked -> Accessibility off
        _log("read_selection: osascript keystroke FAILED (Accessibility not granted?)")
    time.sleep(0.25)                        # let the copy land before reading
    res = _run(["pbpaste"])
    text = (res.stdout if res and res.returncode == 0 else "").strip()
    if text and text == before.strip():
        _log("read_selection: clipboard unchanged after Cmd-C (nothing selected?)")
    return text


def _log(msg):
    """Append a line to the capture log so hotkey issues are debuggable."""
    import datetime
    try:
        from . import paths
        stamp = datetime.datetime.now().isoformat(timespec="seconds")
        with open(os.path.join(paths.get_data_dir(), "capture.log"), "a",
                  encoding="utf-8") as f:
            f.write("%s  %s\n" % (stamp, msg))
    except OSError:
        pass


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
    """Translate `text` into `target` ('en' or 'it').

    Fast online first (webtranslate, both directions, auto-detect); offline it
    falls back to the Apple 'itacli Translate' Shortcut (Italian->English only).
    Returns "" if nothing works.
    """
    from . import webtranslate
    out = webtranslate.translate(text, target)
    if out:
        return out
    if target == "en":                          # offline fallback (Apple, IT->EN)
        name = db.get_setting("translate_shortcut", "")
        if name and name in _installed_shortcuts():
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


def _is_native(text):
    """True if the selection is the user's NATIVE (non-Italian) language, so we
    translate the other way. Uses py3langid, with an Italian-function-word
    override for short strings it gets wrong."""
    t = (text or "").strip()
    if not t:
        return False
    from . import sources
    if sources.italian_ratio(t) >= 0.2:          # clearly Italian function words
        return False
    try:
        import py3langid as langid
        return langid.classify(t)[0] != "it"
    except Exception:
        return False                              # unsure -> treat as Italian


def _canonical(term, context=None):
    """Return (italian_form, pos, gender, tense_concept). A single Italian word
    becomes its LEMMA (un-conjugated: 'vado'->'andare', 'gatti'->'gatto');
    phrases stay as-is. Verbs use the reliable mlconjug3 reverse index first,
    then spaCy."""
    from . import morph, unconjugate
    if " " in term.strip() or not term.strip().isalpha():
        return term.strip(), None, None, None
    pos, gender, lemma = morph.analyze(term, context)
    inf = unconjugate.infinitive(term)
    if pos == "verb" or (inf and pos is None):
        pos = "verb"
        if inf:
            lemma = inf                     # trustworthy for common verbs
        tense = morph.verb_concept(term, context)
    else:
        tense = None
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

    from . import webtranslate
    # one fast call: translate the whole selection + learn its language
    full_en, src = webtranslate.translate_detect(text, "en")
    native = (src != "it") if src else _is_native(text)   # web detect, else offline guess

    terms = chunk(text)[:8]
    if native:                              # native words -> Italian (one batch call)
        italians = webtranslate.translate_many(terms, "it")
        cards = [_canonical(it) + (word,)   # (it_form, pos, gender, tense, english)
                 for word, it in zip(terms, italians) if it]
    else:                                   # Italian -> canonicalise, then batch gloss
        canon = [_canonical(t, text) for t in terms]
        glosses = webtranslate.translate_many([c[0] for c in canon], "en")
        cards = [c + (g,) for c, g in zip(canon, glosses)]

    added, skipped, seen = [], [], set()
    anki_up = anki.is_available()
    for it_form, pos, gender, tense, english in cards:
        if not it_form or it_form.lower() in seen or _already_have(it_form):
            continue
        seen.add(it_form.lower())
        note_id = anki.add_card(it_form, english) if anki_up else None   # front=IT, back=EN
        _save_vocab(it_form, english, pos, gender, tense, text, note_id)
        (added if note_id or not anki_up else skipped).append(it_form)
    if anki_up:                             # (2/3) drain the backlog now Anki is up
        from . import sync
        sync.flush()
    if notify and db.get_setting("show_popup", "1") == "1":
        _show_translation_popup(text, full_en)
    return {
        "captured": text,
        "added": added,
        "skipped": skipped,
        "anki": anki_up,
    }


def _notify(title, message):
    """Show the native-looking floating panel; fall back to an osascript dialog."""
    from . import popover
    if popover.show(message):
        return
    t = message.replace('"', "'")
    _run(["osascript", "-e",
          'display dialog "%s" with title "itacli" buttons {"OK"} '
          'default button "OK" giving up after 8 with icon note' % t])


def _show_translation_popup(text, full_translation=None):
    """The translate popup: show the selection's translation near the cursor."""
    trans = full_translation or translate(text)
    if trans:
        snippet = text if len(text) <= 40 else text[:37] + "..."
        _notify("itacli", "%s  →  %s" % (snippet, trans))


def capture_once():
    """One capture cycle (entry point for `run.py capture` / an OS binding)."""
    _log("capture fired")
    text = read_selection()
    result = capture_pipeline(text, notify=True)
    _log("captured=%r added=%s anki=%s" % (result.get("captured", "")[:60],
                                           result.get("added"), result.get("anki")))
    _report(result)


def listen():
    """Global-hotkey daemon on the shortcut from Settings (needs pynput). This is
    a TRUE global hotkey (apps can't override it, unlike a Services shortcut)."""
    hotkey = db.get_setting("capture_hotkey", "<cmd>+<shift>+i")
    try:
        from pynput import keyboard
    except ImportError:
        print("The hotkey daemon needs pynput:  .venv/bin/python -m pip install pynput")
        return
    try:
        from . import hotkeys
        pretty = hotkeys.human(hotkey)
    except Exception:
        pretty = hotkey
    print("\nitacli is listening for  %s  - select text anywhere and press it." % pretty)
    print("Keep this window open. Press Ctrl-C to stop.")
    print("(If nothing happens on press, macOS needs Accessibility for THIS")
    print(" terminal: System Settings > Privacy & Security > Accessibility.)\n")
    _log("listen started for %s" % hotkey)

    import time
    kbd = keyboard.Controller()

    def on_fire():
        # The hotkey's modifiers (Cmd/Shift/...) are still held here; release them
        # so the ⌘C we send actually copies the SELECTION (not a stale clipboard).
        for k in (keyboard.Key.cmd, keyboard.Key.shift, keyboard.Key.alt,
                  keyboard.Key.ctrl, keyboard.Key.cmd_r, keyboard.Key.shift_r):
            try:
                kbd.release(k)
            except Exception:
                pass
        time.sleep(0.15)
        print("  ... hotkey! capturing", flush=True)
        capture_once()

    try:
        with keyboard.GlobalHotKeys({hotkey: on_fire}) as h:
            h.join()
    except Exception as e:
        print("Hotkey listener error: %s" % e)
        _log("listen error: %s" % e)


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
