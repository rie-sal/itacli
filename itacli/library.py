"""Reading library (SPECS §8 Content library).

Texts live as plain .txt files in the profile's `library/` folder - so you can
also drop/organise files there from Finder or the shell and they just appear in
the reader. Downloads from Project Gutenberg land here too. The reader's
"choose a text" lists this library; browsing/adding/deleting happens here.
"""
import os

from . import db, paths


def folder():
    return paths.library_dir()


def _title_from(filename):
    return os.path.splitext(filename)[0].replace("_", " ").replace("-", " ").strip()


def items():
    """Text files in the library, each as {id, title, file}."""
    out = []
    for fn in sorted(os.listdir(folder())):
        if fn.lower().endswith(".txt"):
            out.append({"id": "lib:" + fn, "title": _title_from(fn), "file": fn})
    return out


def load_text(fn):
    with open(os.path.join(folder(), fn), encoding="utf-8", errors="replace") as f:
        return f.read()


def add_gutenberg(book_id, title=None):
    """Download a Gutenberg text into the library. Returns the filename. Raises
    RuntimeError on fetch failure."""
    from . import reading
    text = reading.fetch_book(book_id)          # network; may raise RuntimeError
    name = paths.slug(title or ("gutenberg-%s" % book_id))
    fn = "%s.txt" % name
    with open(os.path.join(folder(), fn), "w", encoding="utf-8") as f:
        f.write(text)
    return fn


def delete(fn):
    path = os.path.join(folder(), fn)
    if os.path.exists(path):
        os.remove(path)
    # drop saved reading progress for this item
    bid = "lib:" + fn
    conn = db.connect()
    try:
        conn.execute("DELETE FROM settings WHERE key IN (?, ?)",
                     ("read_line_%s" % bid, "read_total_%s" % bid))
        conn.commit()
    finally:
        conn.close()


def search_gutenberg(query, limit=10):
    """Search Project Gutenberg (Italian) via the Gutendex API. Best-effort."""
    import json
    import urllib.error
    import urllib.parse
    import urllib.request
    url = ("https://gutendex.com/books?languages=it&search="
           + urllib.parse.quote(query))
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "itacli/0.0.1"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8", "replace"))
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise RuntimeError("Gutenberg search failed (%s)" % e)
    out = []
    for b in data.get("results", [])[:limit]:
        author = b["authors"][0]["name"] if b.get("authors") else ""
        out.append({"id": str(b["id"]), "title": b.get("title", ""), "author": author})
    return out
