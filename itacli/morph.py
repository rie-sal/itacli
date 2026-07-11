"""Italian morphology for deterministic exercise generation (SPECS §7-grammar).

Correctness-first: every generator returns a form ONLY when the rule is
unambiguous, else None (so the template picks a different word). Verb
conjugation and full coverage plug in via mlconjug3 / Morph-it! when installed;
until then we stick to the safe, rule-governed transformations (articles,
regular plurals) that can't silently produce a wrong answer.
"""
_VOWELS = "aeiou"


def guess_features(word):
    """Heuristic (pos, gender) from word endings. Upgraded by spaCy/Morph-it!
    when available. Returns (pos|None, gender|None)."""
    w = word.strip().lower()
    if not w.isalpha():
        return None, None
    if len(w) > 3 and w.endswith(("are", "ere", "ire")):
        return "verb", None
    if w.endswith("o"):
        return "noun", "m"
    if w.endswith("a"):
        return "noun", "f"
    if w.endswith("e"):
        return "noun", None      # gender genuinely ambiguous
    return None, None


def _needs_lo(w):
    """True if a masculine noun takes lo/gli/uno (s+consonant, z, gn, ps...)."""
    w = w.lower()
    if w.startswith(("gn", "pn", "ps", "x", "y", "z")):
        return True
    return w[0] == "s" and len(w) > 1 and w[1] not in _VOWELS


def _starts_vowel(w):
    return w[:1].lower() in _VOWELS


def definite_article(gender, number, noun):
    """il/lo/la/i/gli/le. Returns None for vowel-initial (apostrophe) cases so
    the answer stays a clean standalone word."""
    if gender not in ("m", "f") or _starts_vowel(noun):
        return None
    if number == "s":
        if gender == "m":
            return "lo" if _needs_lo(noun) else "il"
        return "la"
    if gender == "m":
        return "gli" if _needs_lo(noun) else "i"
    return "le"


def indefinite_article(gender, noun):
    """un/uno/una. None for vowel-initial feminine (un') to keep it clean."""
    if gender == "m":
        return "uno" if _needs_lo(noun) else "un"
    if gender == "f":
        return None if _starts_vowel(noun) else "una"
    return None


def pluralize(noun, gender):
    """Regular plural, or None when the ending is exception-prone."""
    n = noun.strip().lower()
    if not n.isalpha() or len(n) < 3:
        return None
    # skip endings with common irregulars / spelling shifts
    if n.endswith(("io", "co", "go", "ca", "ga", "cia", "gia", "ista", "tà")):
        return None
    if n.endswith("o"):
        return n[:-1] + "i"
    if n.endswith("e"):
        return n[:-1] + "i"
    if n.endswith("a"):
        return n[:-1] + "e" if gender == "f" else None
    return None


# --- spaCy analyzer (tagging) + mlconjug3 conjugator (verbs) ----------------
# Both load lazily and cache; if unavailable, we fall back to the heuristic /
# skip verb exercises, so the app still runs on plain stdlib Python.

_NLP = None
_CONJ = None
SPACY_MODEL = "it_core_news_md"
_POS_MAP = {"NOUN": "noun", "PROPN": "noun", "VERB": "verb", "AUX": "verb",
            "ADJ": "adj", "ADV": "adv"}


def _nlp():
    global _NLP
    if _NLP is None:
        try:
            import spacy
            _NLP = spacy.load(SPACY_MODEL)
        except Exception:
            _NLP = False
    return _NLP or None


def analyze(word):
    """Return (pos, gender, lemma) using spaCy when available, else heuristic."""
    nlp = _nlp()
    if nlp and word:
        toks = [t for t in nlp(word) if t.is_alpha]
        if toks:
            t = toks[0]
            pos = _POS_MAP.get(t.pos_)
            g = t.morph.get("Gender")
            gender = {"Masc": "m", "Fem": "f"}.get(g[0]) if g else None
            return pos, gender, t.lemma_.lower()
    pos, gender = guess_features(word)
    return pos, gender, (word or "").strip().lower()


def _conjugator():
    global _CONJ
    if _CONJ is None:
        try:
            import warnings
            warnings.filterwarnings("ignore")
            import mlconjug3
            _CONJ = mlconjug3.Conjugator(language="it")
        except Exception:
            _CONJ = False
    return _CONJ or None


def conjugate(infinitive, person="1s", mood="Indicativo", tense="Indicativo presente"):
    """Conjugate a verb via mlconjug3, or None if unavailable/unknown.

    person: one of 1s 2s 3s 1p 2p 3p. Returns None rather than risk a guess.
    """
    conj = _conjugator()
    if not conj or not infinitive:
        return None
    try:
        info = conj.conjugate(infinitive).conjug_info.get(mood, {}).get(tense, {})
        return info.get(person) or None
    except Exception:
        return None


def backend_status():
    return {"builtin": True, "spacy": _nlp() is not None,
            "mlconjug3": _conjugator() is not None}
