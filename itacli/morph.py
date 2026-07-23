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


def _tok_info(t):
    pos = _POS_MAP.get(t.pos_)
    g = t.morph.get("Gender")
    gender = {"Masc": "m", "Fem": "f"}.get(g[0]) if g else None
    return pos, gender, t.lemma_.lower()


def _find_token(word, context):
    """Locate `word` inside its sentence so spaCy lemmatises it IN CONTEXT
    (crucial for irregulars: 'vado' -> 'andare' only works with context)."""
    nlp = _nlp()
    if not (nlp and context):
        return None
    wl = word.strip().lower()
    for t in nlp(context):
        if t.is_alpha and t.text.lower() == wl:
            return t
    return None


def analyze(word, context=None):
    """Return (pos, gender, lemma). Uses the sentence `context` when given so
    irregular forms lemmatise correctly; falls back to the word alone, then a
    heuristic."""
    nlp = _nlp()
    if nlp and word:
        t = _find_token(word, context)
        if t is not None:
            return _tok_info(t)
        toks = [tk for tk in nlp(word) if tk.is_alpha]
        if toks:
            return _tok_info(toks[0])
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


# Grammar-concept key -> (mlconjug3 mood, tense) for exercise generation.
VERB_TENSE = {
    "present-tense": ("Indicativo", "Indicativo presente"),
    "passato-prossimo": ("Indicativo", "Indicativo passato prossimo"),
    "imperfetto": ("Indicativo", "Indicativo imperfetto"),
    "futuro": ("Indicativo", "Indicativo futuro semplice"),
    "passato-remoto": ("Indicativo", "Indicativo passato remoto"),
    "trapassato-prossimo": ("Indicativo", "Indicativo trapassato prossimo"),
    "futuro-anteriore": ("Indicativo", "Indicativo futuro anteriore"),
    "congiuntivo": ("Congiuntivo", "Congiuntivo presente"),
    "congiuntivo-imperfetto": ("Congiuntivo", "Congiuntivo imperfetto"),
    "congiuntivo-passato": ("Congiuntivo", "Congiuntivo passato"),
    "congiuntivo-trapassato": ("Congiuntivo", "Congiuntivo trapassato"),
    "conditional": ("Condizionale", "Condizionale presente"),
    "condizionale-passato": ("Condizionale", "Condizionale passato"),
}


def conjugate_concept(infinitive, concept, person="1s"):
    """Conjugate for a grammar-concept key (e.g. 'imperfetto'). None if unknown."""
    mt = VERB_TENSE.get(concept)
    if not mt:
        return None
    return conjugate(infinitive, person=person, mood=mt[0], tense=mt[1])


def verb_concept(word, context=None):
    """Detect which tense/mood concept a conjugated verb is in (for the tally).
    Uses sentence context when given. Returns a key from VERB_TENSE or None."""
    nlp = _nlp()
    if not nlp or not word:
        return None
    t = _find_token(word, context)
    if t is None or t.pos_ not in ("VERB", "AUX"):
        toks = [tk for tk in nlp(word) if tk.pos_ in ("VERB", "AUX")]
        if not toks:
            return None
        t = toks[0]
    mood = (t.morph.get("Mood") or [""])[0]
    tense = (t.morph.get("Tense") or [""])[0]
    if mood == "Sub":
        return "congiuntivo-imperfetto" if tense == "Imp" else "congiuntivo"
    if mood == "Cnd":
        return "conditional"
    if tense == "Imp":
        return "imperfetto"
    if tense == "Past":
        return "passato-prossimo"
    if tense == "Fut":
        return "futuro"
    if tense == "Pres":
        return "present-tense"
    return None


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
