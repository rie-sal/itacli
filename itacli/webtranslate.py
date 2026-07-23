"""Fast online translation (SPECS §7-vocab, §10).

Uses Google's public translate endpoint: fast (~0.2-0.6s), both directions, and
it AUTO-DETECTS the source language - so a highlighted word gets translated the
right way with no guessing, and it's far faster than one-Shortcut-call-per-word.
Stdlib only, no key. Returns None when offline, so callers fall back to Apple's
on-device Shortcut (and, later, Argos for full offline).
"""
import json
import urllib.error
import urllib.parse
import urllib.request

ENDPOINT = "https://translate.googleapis.com/translate_a/single"


def translate_detect(text, target, timeout=6):
    """Return (translated_text, detected_source_lang) or (None, None) if offline."""
    text = (text or "").strip()
    if not text:
        return None, None
    url = "%s?client=gtx&sl=auto&tl=%s&dt=t&q=%s" % (
        ENDPOINT, target, urllib.parse.quote(text))
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
        translated = "".join(s[0] for s in data[0] if s and s[0]).strip()
        detected = data[2] if len(data) > 2 else None
        return (translated or None), detected
    except (urllib.error.URLError, OSError, ValueError, IndexError, KeyError):
        return None, None


def translate(text, target):
    return translate_detect(text, target)[0]


def translate_many(texts, target, timeout=8):
    """Translate several short strings in ONE call (avoids per-word rate limits).
    Returns a list aligned with `texts` ('' where unavailable)."""
    items = [t.strip() for t in texts]
    if not items:
        return []
    q = "\n".join(items)
    url = "%s?client=gtx&sl=auto&tl=%s&dt=t&q=%s" % (
        ENDPOINT, target, urllib.parse.quote(q))
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
        segs = [s[0].strip() for s in data[0] if s and s[0]]
    except (urllib.error.URLError, OSError, ValueError, IndexError, KeyError):
        return ["" for _ in items]
    if len(segs) == len(items):
        return segs
    return (segs + [""] * len(items))[:len(items)]   # best-effort alignment
