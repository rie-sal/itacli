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
import shutil
import textwrap
import urllib.error
import urllib.request

from . import anki, capture, db, paths, study, ui

# Best-effort curated Italian texts. If a fetch fails, the reader falls back to
# the bundled excerpt below, so the pillar always works offline.
CURATED = [
    {"id": "52484", "title": "Le avventure di Pinocchio", "author": "Carlo Collodi"},
    {"id": "45334", "title": "I promessi sposi", "author": "Alessandro Manzoni"},
    {"id": "997", "title": "La Divina Commedia: Inferno", "author": "Dante Alighieri"},
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
    """Drop the Project Gutenberg license header/footer (handles both the
    '*** START OF' and older '***START OF' marker formats)."""
    starts = list(re.finditer(r"\*\*\* *START OF .*?\*\*\*", text, re.I))
    if starts:
        text = text[starts[-1].end():]
    end = re.search(r"\*\*\* *END OF .*?\*\*\*", text, re.I)
    if end:
        text = text[:end.start()]
    return text.strip()


_AUDIO_MARKERS = ("librivox", "audio reading", "audiobook", "audio recording",
                  "public domain certification", "this recording is in the public")


def _looks_like_audiobook(text):
    """True for a short LibriVox/audiobook companion blurb (not a real book)."""
    head = text[:1500].lower()
    has_marker = any(m in head for m in _AUDIO_MARKERS)
    return has_marker and len(text) < 8000


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
            if _looks_like_audiobook(text):
                raise RuntimeError(
                    "That entry is an audiobook companion blurb, not a readable "
                    "book - skipping. (It may work as a Listening source later.)")
            with open(cached, "w", encoding="utf-8") as f:
                f.write(text)
            return text
        except (urllib.error.URLError, OSError) as e:
            last = e
    raise RuntimeError("Could not fetch Gutenberg #%s (%s)" % (book_id, last))


def _display_lines(text):
    """Wrap the whole text to the measure, preserving paragraph breaks, into a
    flat list of display lines we can paginate."""
    lines = []
    for para in text.split("\n\n"):
        para = para.strip()
        if not para:
            continue
        lines.extend(textwrap.wrap(para, ui.WIDTH) or [""])
        lines.append("")   # blank line between paragraphs
    while lines and lines[-1] == "":
        lines.pop()
    return lines


def _page_height():
    """How many text lines fit a page, after header/rule/footer chrome."""
    rows = shutil.get_terminal_size((80, 24)).lines
    return max(6, rows - 9)


def _line_key(book_id):
    return "read_line_%s" % book_id


def _total_key(book_id):
    return "read_total_%s" % book_id


def _progress_pct(book_id):
    """Saved reading progress as a percent, or None if never opened."""
    total = int(db.get_setting(_total_key(book_id), "0"))
    if total <= 0:
        return None
    pos = int(db.get_setting(_line_key(book_id), "0"))
    return min(100, int(pos / total * 100))


def _pct_suffix(book_id):
    pct = _progress_pct(book_id)
    return "   (%d%%)" % pct if pct is not None else ""


def save_word(term, context):
    """Un-conjugate + gloss + push to Anki (front=Italian, back=English) + record
    in vocab. Dedupes by canonical form. Reading is always Italian text."""
    term = term.strip()
    if not term:
        return None
    it_form, pos, gender, tense = capture._canonical(term, context)
    if capture._already_have(it_form):
        return None
    english = capture.translate(it_form)
    note_id = anki.add_card(it_form, english) if anki.is_available() else None
    conn = db.connect()
    try:
        conn.execute(
            "INSERT INTO vocab(term, gloss, source_context, status, "
            "anki_note_id, added_from, pos, gender, lemma, features) "
            "VALUES (?, ?, ?, 'new', ?, 'reading', ?, ?, ?, ?)",
            (it_form, english, context, note_id, pos, gender, it_form, tense),
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
    from . import morph
    concept = morph.verb_concept(answer, paragraph)   # route verb clozes -> concept
    _record_attempt(correct, "grammar:%s" % concept if concept else "reading-cloze")
    ui.line("  " + ("correct!" if correct else "the word was: %s" % answer))
    try:
        input(ui.INDENT + "  press Enter ")
    except EOFError:
        return


def _read_book(book):
    text = book.get("text")
    if text is None:
        ui.clear()
        ui.blank()
        ui.line("Fetching '%s' from Project Gutenberg..." % book.get("title", ""))
        ui.line("(first time only - it's cached afterwards)")
        try:
            text = fetch_book(book["id"])
        except RuntimeError as e:
            ui.panel("Reading", [str(e), "", "Falling back to the bundled excerpt."])
            book = SAMPLE
            text = SAMPLE["text"]
    bid = book["id"]
    lines = _display_lines(text)
    total = len(lines)
    db.set_setting(_total_key(bid), total)
    pos = int(db.get_setting(_line_key(bid), "0"))
    if pos >= total:          # finished last time -> start over
        pos = 0

    with study.Timer():
        while 0 <= pos < total:
            ph = _page_height()
            page = lines[pos:pos + ph]
            pct = int(min(pos + ph, total) / total * 100)
            total_pages = max(1, -(-total // ph))
            page_num = min(total_pages, pos // ph + 1)
            ui.clear()
            ui.blank()
            ui.two_sided(book["title"],
                         "page %d of %d · %d%%" % (page_num, total_pages, pct))
            ui.blank()
            ui.rule()
            ui.blank()
            for wline in page:
                ui.line(wline)
            ui.blank()
            ui.rule()
            ui.line("[Enter] next  ·  [b] back  ·  [s] save word(s)  ·  "
                    "[c] check  ·  [q] quit")
            ui.blank()
            try:
                raw = input(ui.INDENT + "> ").strip().lower()
            except EOFError:
                break
            if raw in ("q", "quit"):
                break
            if raw in ("b", "back"):
                pos = max(0, pos - ph)
            elif raw == "s":
                _save_from_page("\n".join(page))
            elif raw == "c":
                _run_cloze(" ".join(page))
            else:
                pos += ph
            db.set_setting(_line_key(bid), min(pos, total))

    if pos >= total:
        ui.panel("Reading", ["You reached the end of this text. Complimenti!"])


def _save_from_page(page_text):
    try:
        raw = input(ui.INDENT + "  words to save (comma-separated): ").strip()
    except EOFError:
        return
    words = [w.strip() for w in raw.split(",") if w.strip()]
    if not words:
        return
    for w in words:
        save_word(w, page_text)
    up = anki.is_available()
    ui.line("  saved %d word(s)%s." % (
        len(words), "" if up else " (vocab only - open Anki to sync cards)"))
    try:
        input(ui.INDENT + "  press Enter ")
    except EOFError:
        return


def _read_mediawiki(kind, fetch):
    try:
        title = input(ui.INDENT + "%s title (e.g. Pinocchio): " % kind).strip()
    except EOFError:
        return
    if not title:
        return
    try:
        text = fetch(title)
    except RuntimeError as e:
        ui.panel(kind, [str(e)])
        return
    _read_book({"id": "%s:%s" % (kind.lower(), title), "title": title,
                "author": kind, "text": text})


def _read_wikisource():
    from . import sources
    _read_mediawiki("Wikisource", sources.wikisource_text)


def _read_wikipedia():
    from . import sources
    _read_mediawiki("Wikipedia", sources.wikipedia_text)


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


def _add_gutenberg_flow(library, rel):
    ui.blank()
    for j, b in enumerate(CURATED, start=1):
        ui.line("  s%d  %s - %s" % (j, b["title"], b["author"]))
    ui.line("  or type a Gutenberg ID / search terms")
    try:
        q = input(ui.INDENT + "  > ").strip()
    except EOFError:
        return
    if not q:
        return
    book_id, title = None, None
    if q.lower().startswith("s") and q[1:].isdigit() and 1 <= int(q[1:]) <= len(CURATED):
        b = CURATED[int(q[1:]) - 1]
        book_id, title = b["id"], b["title"]
    elif q.isdigit():
        book_id = q
    else:
        try:
            results = library.search_gutenberg(q)
        except RuntimeError as e:
            ui.panel("Add text", [str(e)])
            return
        if not results:
            ui.panel("Add text", ["No Italian results."])
            return
        ui.blank()
        for i, r in enumerate(results, 1):
            ui.line("  %d  %s - %s  (#%s)" % (i, r["title"][:40], r["author"][:20], r["id"]))
        try:
            pick = input(ui.INDENT + "  download which? ").strip()
        except EOFError:
            return
        if pick.isdigit() and 1 <= int(pick) <= len(results):
            book_id, title = results[int(pick) - 1]["id"], results[int(pick) - 1]["title"]
    if not book_id:
        return
    ui.line("  downloading #%s ..." % book_id)
    try:
        library.add_gutenberg(book_id, title, rel)
        ui.line("  added.")
    except Exception as e:
        ui.line("  couldn't add: %s" % e)
    try:
        input(ui.INDENT + "  press Enter ")
    except EOFError:
        pass


def _organize_flow(library, rel, files):
    ui.blank()
    ui.line("  organize: [mkdir NAME] [rename N NEWNAME] [move N FOLDER] [q]")
    try:
        cmd = input(ui.INDENT + "  > ").strip()
    except EOFError:
        return
    parts = cmd.split()
    if not parts or parts[0].lower() == "q":
        return
    op = parts[0].lower()
    try:
        if op == "mkdir" and len(parts) >= 2:
            library.mkdir(rel, " ".join(parts[1:]))
        elif op == "rename" and len(parts) >= 3 and parts[1].isdigit():
            library.rename(rel, files[int(parts[1]) - 1], " ".join(parts[2:]))
        elif op == "move" and len(parts) >= 3 and parts[1].isdigit():
            library.move(rel, files[int(parts[1]) - 1], parts[2])
        else:
            ui.line("  didn't understand that.")
    except (IndexError, OSError) as e:
        ui.line("  error: %s" % e)


def open_reading():
    """Browse your library (with sub-folders) or a web source, then read."""
    from . import library
    rel = ""
    while True:
        dirs, files = library.list_dir(rel)
        ui.clear()
        ui.blank()
        ui.two_sided("Reading & library", "/" + rel if rel else "/")
        ui.blank()
        ui.rule()
        ui.blank()
        entries = []                         # index -> ("sample"|"dir"|"file", value)
        if rel:
            ui.line("0  .. (up a folder)")
        n = 1
        if not rel:
            ui.line("%d  %s%s  (bundled)" % (n, SAMPLE["title"], _pct_suffix("sample")))
            entries.append(("sample", None))
            n += 1
        for d in dirs:
            ui.line("%d  %s/" % (n, d))
            entries.append(("dir", d))
            n += 1
        for f in files:
            ui.line("%d  %s%s" % (n, library._title_from(f),
                                  _pct_suffix(library.item_id(rel, f))))
            entries.append(("file", f))
            n += 1
        if not files and not dirs and rel:
            ui.line("   (empty folder)")
        ui.blank()
        ui.line("web:   w Wikisource   p Wikipedia   r Reddit   g Gutenberg ID")
        ui.line("files: a add-text   d delete N   o open folder in Finder   m organize")
        ui.line("q back      folder: %s" % library._abs(rel))
        ui.blank()
        ui.rule()
        ui.blank()
        try:
            choice = input(ui.INDENT + "> ").strip().lower()
        except EOFError:
            return
        if choice in ("q", ""):
            return
        if choice == "0" and rel:
            rel = os.path.dirname(rel)
        elif choice == "w":
            _read_wikisource()
        elif choice == "p":
            _read_wikipedia()
        elif choice == "r":
            _read_reddit()
        elif choice == "g":
            try:
                bid = input(ui.INDENT + "Gutenberg ID: ").strip()
            except EOFError:
                continue
            if bid:
                _read_book({"id": bid, "title": "Gutenberg #%s" % bid, "author": ""})
        elif choice == "a":
            _add_gutenberg_flow(library, rel)
        elif choice == "o":
            library.open_in_finder(rel)
        elif choice == "m":
            _organize_flow(library, rel, files)
        elif choice.startswith("d") and choice[1:].strip().isdigit():
            k = int(choice[1:].strip()) - 1
            if 0 <= k < len(entries) and entries[k][0] == "file":
                library.delete(rel, entries[k][1])
        elif choice.isdigit() and 1 <= int(choice) <= len(entries):
            kind, val = entries[int(choice) - 1]
            if kind == "sample":
                _read_book(SAMPLE)
            elif kind == "dir":
                rel = os.path.join(rel, val) if rel else val
            else:
                _read_book({"id": library.item_id(rel, val),
                            "title": library._title_from(val),
                            "text": library.load_text(rel, val)})
