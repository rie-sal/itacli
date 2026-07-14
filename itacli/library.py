"""Reading library (SPECS §8, folded into Reading).

Texts are plain .txt files under the profile's `library/` folder, which may
contain SUB-FOLDERS you navigate in the reader. Organise them from Finder/shell
or with the in-app commands. Gutenberg downloads land here too.
"""
import os
import subprocess
import sys

from . import db, paths


def folder():
    return paths.library_dir()


def _abs(rel):
    return os.path.join(folder(), rel) if rel else folder()


def _title_from(filename):
    return os.path.splitext(filename)[0].replace("_", " ").replace("-", " ").strip()


def list_dir(rel=""):
    """(subfolders, txt files) inside library/<rel>."""
    base = _abs(rel)
    dirs, files = [], []
    if os.path.isdir(base):
        for name in sorted(os.listdir(base)):
            p = os.path.join(base, name)
            if os.path.isdir(p):
                dirs.append(name)
            elif name.lower().endswith(".txt"):
                files.append(name)
    return dirs, files


def item_id(rel, filename):
    return "lib:" + (os.path.join(rel, filename) if rel else filename)


def load_text(rel, filename):
    with open(_abs(os.path.join(rel, filename)), encoding="utf-8", errors="replace") as f:
        return f.read()


def add_gutenberg(book_id, title=None, rel=""):
    """Download a Gutenberg text into library/<rel>. Raises on failure (incl.
    audiobook blurbs). Returns the filename."""
    from . import reading
    text = reading.fetch_book(book_id)
    name = paths.slug(title or ("gutenberg-%s" % book_id)) + ".txt"
    with open(_abs(os.path.join(rel, name)), "w", encoding="utf-8") as f:
        f.write(text)
    return name


def delete(rel, filename):
    path = _abs(os.path.join(rel, filename))
    if os.path.exists(path):
        os.remove(path)
    bid = item_id(rel, filename)
    conn = db.connect()
    try:
        conn.execute("DELETE FROM settings WHERE key IN (?, ?)",
                     ("read_line_%s" % bid, "read_total_%s" % bid))
        conn.commit()
    finally:
        conn.close()


def mkdir(rel, name):
    os.makedirs(_abs(os.path.join(rel, paths.slug(name))), exist_ok=True)


def rename(rel, filename, newname):
    if not newname.lower().endswith(".txt"):
        newname += ".txt"
    os.rename(_abs(os.path.join(rel, filename)), _abs(os.path.join(rel, newname)))


def move(rel, filename, dest_rel):
    dst = _abs(os.path.join(dest_rel, filename))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    os.rename(_abs(os.path.join(rel, filename)), dst)


def open_in_finder(rel=""):
    if sys.platform == "darwin":
        try:
            subprocess.run(["open", _abs(rel)], capture_output=True, timeout=8)
        except (OSError, subprocess.SubprocessError):
            pass


def search_gutenberg(query, limit=10):
    """Search Project Gutenberg (Italian) via Gutendex. Best-effort."""
    import json
    import urllib.error
    import urllib.parse
    import urllib.request
    url = "https://gutendex.com/books?languages=it&search=" + urllib.parse.quote(query)
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
