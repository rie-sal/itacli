"""Reading pillar - build step 1, the spine (SPECS §7-reading).

Source: Project Gutenberg (stdlib urllib; no pip install). Read a passage in
the terminal, name the words you don't know, and each one is glossed and sent
to Anki, and saved to the vocab table for review.

"Highlight" here means typing the unknown words. True click-drag selection
arrives with the Textual UI upgrade; the save loop underneath is identical.
"""
import datetime
import os
import re
import textwrap
import urllib.error
import urllib.request

from . import anki, capture, db, paths, ui

# Best-effort curated Italian texts. If a fetch fails, the reader falls back to
# the bundled excerpt below, so the pillar always works offline.
CURATED = [
    {"id": "24686", "title": "Le avventure di Pinocchio", "author": "Carlo Collodi"},
    {"id": "45334", "title": "I promessi sposi", "author": "Alessandro Manzoni"},
]

SAMPLE = {
    "id": "sample",
    "title": "Le avventure di Pinocchio (excerpt)",
    "author": "Carlo Collodi",
    "text": (
        "C'era una volta...\n\n"
        "— Un re! — diranno subito i miei piccoli lettori.\n\n"
        "No, ragazzi, avete sbagliato. C'era una volta un pezzo di legno.\n\n"
        "Non era un legno di lusso, ma un semplice pezzo da catasta, di quelli "
        "che d'inverno si mettono nelle stufe e nei caminetti per accendere il "
        "fuoco e per riscaldare le stanze.\n\n"
        "Non so come andasse, ma il fatto gli è che un bel giorno questo pezzo "
        "di legno capitò nella bottega di un vecchio falegname, il quale aveva "
        "nome mastr'Antonio, se non che tutti lo chiamavano maestro Ciliegia, "
        "per via della punta del suo naso, che era sempre lustra e paonazza, "
        "come una ciliegia matura."
    ),
}

_URL_PATTERNS = [
    "https://www.gutenberg.org/cache/epub/{id}/pg{id}.txt",
    "https://www.gutenberg.org/files/{id}/{id}-0.txt",
    "https://www.gutenberg.org/files/{id}/{id}.txt",
]


def _strip_gutenberg(text):
    """Drop the Project Gutenberg license header/footer if present."""
    start = text.find("*** START OF")
    if start != -1:
        text = text[text.find("\n", start) + 1:]
    end = text.find("*** END OF")
    if end != -1:
        text = text[:end]
    return text.strip()


def fetch_book(book_id):
    """Return the book text, caching to content_cache/. Raises on failure."""
    cached = os.path.join(paths.content_cache(), "%s.txt" % book_id)
    if os.path.exists(cached):
        with open(cached, encoding="utf-8") as f:
            return f.read()
    last = None
    for pat in _URL_PATTERNS:
        url = pat.format(id=book_id)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "itacli/0.0.1"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = resp.read().decode("utf-8", "replace")
            text = _strip_gutenberg(raw)
            with open(cached, "w", encoding="utf-8") as f:
                f.write(text)
            return text
        except (urllib.error.URLError, OSError) as e:
            last = e
    raise RuntimeError("Could not fetch Gutenberg #%s (%s)" % (book_id, last))


def _paragraphs(text):
    return [p.strip() for p in text.split("\n\n") if p.strip()]


def _pos_key(book_id):
    return "read_pos_%s" % book_id


def save_word(term, context):
    """Gloss + push to Anki + record in vocab (added_from='reading')."""
    term = term.strip()
    if not term:
        return None
    gloss = capture.translate(term)
    note_id = anki.add_card(term, gloss) if anki.is_available() else None
    from . import morph
    pos, gender = morph.guess_features(term)
    conn = db.connect()
    try:
        conn.execute(
            "INSERT INTO vocab(term, gloss, source_context, status, "
            "anki_note_id, added_from, pos, gender) "
            "VALUES (?, ?, ?, 'new', ?, 'reading', ?, ?)",
            (term, gloss, context, note_id, pos, gender),
        )
        conn.commit()
    finally:
        conn.close()
    return note_id


def _norm(word):
    return word.strip().lower().strip(".,;:!?\"'()[]«»…")


def _make_cloze(paragraph):
    """Blank one content word from a sentence. Returns (prompt, answer) or None.

    Deterministic (spaCy-free): picks the first long, non-stopword token.
    """
    for sentence in re.split(r"(?<=[.!?])\s+", paragraph):
        for raw in sentence.split():
            word = raw.strip(".,;:!?\"'()[]«»…")
            if word.isalpha() and len(word) >= 5 and _norm(word) not in capture._STOP:
                blanked = re.sub(r"\b%s\b" % re.escape(word), "_____", sentence, count=1)
                return blanked, word
    return None


def _record_attempt(correct, tag):
    conn = db.connect()
    try:
        conn.execute(
            "INSERT INTO attempts(content_item_id, correct, timestamp, concept_tags) "
            "VALUES (NULL, ?, ?, ?)",
            (1 if correct else 0, datetime.datetime.now().isoformat(timespec="seconds"), tag),
        )
        conn.commit()
    finally:
        conn.close()


def _run_cloze(paragraph):
    """One quick fill-in-the-blank check on the paragraph just read."""
    made = _make_cloze(paragraph)
    if not made:
        return
    prompt, answer = made
    ui.blank()
    ui.line("Quick check - fill the blank (Enter to skip):")
    ui.blank()
    for wline in textwrap.wrap(prompt, ui.WIDTH):
        ui.line(wline)
    ui.blank()
    try:
        guess = input(ui.INDENT + "  = ").strip()
    except EOFError:
        return
    if not guess:
        return
    correct = _norm(guess) == _norm(answer)
    _record_attempt(correct, "reading-cloze")
    ui.line("  " + ("correct!" if correct else "the word was: %s" % answer))
    try:
        input(ui.INDENT + "  press Enter ")
    except EOFError:
        return


def _read_book(book):
    text = book.get("text")
    if text is None:
        try:
            text = fetch_book(book["id"])
        except RuntimeError as e:
            ui.panel("Reading", [str(e), "", "Falling back to the bundled excerpt."])
            book = SAMPLE
            text = SAMPLE["text"]
    paras = _paragraphs(text)
    pos = int(db.get_setting(_pos_key(book["id"]), "0"))

    while pos < len(paras):
        ui.clear()
        ui.blank()
        ui.two_sided(book["title"], "%d / %d" % (pos + 1, len(paras)))
        ui.blank()
        ui.rule()
        ui.blank()
        for wline in textwrap.wrap(paras[pos], ui.WIDTH):
            ui.line(wline)
        ui.blank()
        ui.rule()
        ui.blank()
        ui.line("Type unknown words (comma-separated) to save them,")
        ui.line("Enter to continue, b = back, q = quit reading.")
        ui.blank()
        try:
            raw = input(ui.INDENT + "> ").strip()
        except EOFError:
            break
        if raw.lower() in ("q", "quit"):
            break
        if raw.lower() in ("b", "back"):
            pos = max(0, pos - 1)
            db.set_setting(_pos_key(book["id"]), pos)
            continue
        if raw:
            words = [w.strip() for w in raw.split(",") if w.strip()]
            saved = [w for w in words if save_word(w, paras[pos]) is not None or True]
            up = anki.is_available()
            ui.blank()
            ui.line("Saved %d word(s)%s." % (len(saved),
                    "" if up else " (vocab only - open Anki to sync cards)"))
            try:
                input(ui.INDENT + "  press Enter ")
            except EOFError:
                break
        _run_cloze(paras[pos])
        pos += 1
        db.set_setting(_pos_key(book["id"]), pos)

    if pos >= len(paras):
        ui.panel("Reading", ["You reached the end of this text. Complimenti!"])


def _read_wikisource():
    from . import sources
    try:
        title = input(ui.INDENT + "Wikisource title (e.g. Pinocchio): ").strip()
    except EOFError:
        return
    if not title:
        return
    try:
        text = sources.wikisource_text(title)
    except RuntimeError as e:
        ui.panel("Wikisource", [str(e)])
        return
    _read_book({"id": "wikisource:%s" % title, "title": title,
                "author": "Wikisource", "text": text})


def _read_reddit():
    from . import sources
    interests = db.get_setting("interests", "")
    suggestions = sources.suggest_subreddits(interests)
    ui.clear()
    ui.blank()
    ui.line("Reddit - native-speaker threads")
    ui.blank()
    ui.rule()
    ui.blank()
    ui.line("Suggested (from your interests): " + ", ".join(suggestions))
    ui.blank()
    try:
        sub = input(ui.INDENT + "subreddit (name, blank for %s): " % suggestions[0]).strip()
    except EOFError:
        return
    sub = sub or suggestions[0]
    try:
        posts = sources.reddit_posts(sub)
    except RuntimeError as e:
        ui.panel("Reddit", [str(e)])
        return
    if not posts:
        ui.panel("Reddit", ["No Italian-looking posts found in r/%s right now." % sub])
        return
    text = "\n\n".join(posts)
    _read_book({"id": "reddit:%s" % sub, "title": "r/%s" % sub,
                "author": "Reddit", "text": text})


def open_reading():
    """Menu entry: pick a source, then read."""
    while True:
        ui.clear()
        ui.blank()
        ui.line("Reading - choose a text")
        ui.blank()
        ui.rule()
        ui.blank()
        ui.line("0  Bundled excerpt (offline) - %s" % SAMPLE["title"])
        for i, b in enumerate(CURATED, start=1):
            ui.line("%d  %s - %s  (Gutenberg #%s)" % (i, b["title"], b["author"], b["id"]))
        ui.line("g  Enter any Project Gutenberg ID")
        ui.line("w  Wikisource (enter a title)")
        ui.line("r  Reddit (native-speaker threads)")
        ui.line("q  Back to menu")
        ui.blank()
        ui.rule()
        ui.blank()
        try:
            choice = input(ui.INDENT + "> ").strip().lower()
        except EOFError:
            return
        if choice in ("q", ""):
            return
        if choice == "0":
            _read_book(SAMPLE)
        elif choice == "g":
            try:
                bid = input(ui.INDENT + "Gutenberg ID: ").strip()
            except EOFError:
                return
            if bid:
                _read_book({"id": bid, "title": "Gutenberg #%s" % bid, "author": ""})
        elif choice == "w":
            _read_wikisource()
        elif choice == "r":
            _read_reddit()
        elif choice.isdigit() and 1 <= int(choice) <= len(CURATED):
            _read_book(CURATED[int(choice) - 1])
