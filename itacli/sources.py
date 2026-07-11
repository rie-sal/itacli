"""Live reading sources (SPECS §7-reading, §11): Wikisource + Reddit.

Stdlib urllib + JSON only (no pip). Reddit uses the public unauthenticated
.json endpoints; a lightweight Italian-ness heuristic filters out English-heavy
posts so we lean toward native-speaker text. All fetches fail gracefully.
"""
import json
import urllib.error
import urllib.parse
import urllib.request

UA = {"User-Agent": "itacli/0.0.1 (personal language-learning tool)"}

# Common Italian function words - a cheap language detector (no dependency).
_IT_FUNCTION = set((
    "il lo la i gli le un uno una di a da in con su per tra fra e ed o ma che "
    "non si se come anche del della dei delle al alla allo nel nella sul sulla "
    "è sono ho hai ha abbiamo mi ti ci vi questo questa quello quella più "
    "molto quando perché dove chi cosa fare essere ne lo suo sua").split())

# Best-effort interest -> Italian subreddits. Manual entry is the reliable path;
# these are only suggestions and are still passed through the language filter.
SUBS_BY_INTEREST = {
    "calcio": ["calcio"], "sport": ["calcio"],
    "cinema": ["cinema"], "film": ["cinema"],
    "libri": ["Libri"], "books": ["Libri"], "reading": ["Libri"],
    "tecnologia": ["ItalyInformatica"], "technology": ["ItalyInformatica"],
    "programming": ["ItalyInformatica"], "musica": ["Musica"], "music": ["Musica"],
    "storia": ["Italia"], "history": ["Italia"], "news": ["Italia"],
    "roma": ["roma"], "milano": ["Milano"], "firenze": ["Firenze"],
}
DEFAULT_SUBS = ["Italia", "AskItaly"]


def italian_ratio(text):
    toks = [t.strip(".,;:!?\"'()[]«»…").lower() for t in text.split()]
    toks = [t for t in toks if t.isalpha()]
    if not toks:
        return 0.0
    return sum(1 for t in toks if t in _IT_FUNCTION) / len(toks)


def _get_json(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=12) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def suggest_subreddits(interests):
    """Map comma-separated interests to suggested Italian subs."""
    out = []
    for word in [w.strip().lower() for w in (interests or "").split(",") if w.strip()]:
        out.extend(SUBS_BY_INTEREST.get(word, []))
    for s in DEFAULT_SUBS:
        if s not in out:
            out.append(s)
    seen, uniq = set(), []
    for s in out:
        if s.lower() not in seen:
            seen.add(s.lower())
            uniq.append(s)
    return uniq


def reddit_posts(subreddit, limit=10, min_italian=0.20):
    """Return Italian-looking post texts from a subreddit's hot feed."""
    url = "https://www.reddit.com/r/%s/hot.json?limit=%d" % (
        urllib.parse.quote(subreddit), limit)
    try:
        data = _get_json(url)
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise RuntimeError("Could not fetch r/%s (%s)" % (subreddit, e))
    posts = []
    for child in data.get("data", {}).get("children", []):
        d = child.get("data", {})
        if d.get("stickied"):
            continue
        text = d.get("title", "")
        if d.get("selftext"):
            text += "\n\n" + d["selftext"]
        text = text.strip()
        if text and italian_ratio(text) >= min_italian:
            posts.append(text)
    return posts


def wikisource_text(title, lang="it"):
    """Plain-text extract of a Wikisource page via the MediaWiki API."""
    api = "https://%s.wikisource.org/w/api.php?" % lang
    params = {
        "action": "query", "prop": "extracts", "explaintext": "1",
        "titles": title, "format": "json", "redirects": "1",
    }
    try:
        data = _get_json(api + urllib.parse.urlencode(params))
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise RuntimeError("Could not fetch Wikisource '%s' (%s)" % (title, e))
    pages = data.get("query", {}).get("pages", {})
    for page in pages.values():
        extract = page.get("extract", "").strip()
        if extract:
            return extract
    raise RuntimeError("No text found for Wikisource '%s'" % title)
