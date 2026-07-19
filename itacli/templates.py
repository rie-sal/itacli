"""Grammar exercise templates (SPECS §7-grammar).

A template encodes a grammar CONCEPT, not specific words. Given a vocab item
(term + tagged features) it produces a fill-in-the-blank exercise whose answer
is GENERATED deterministically by morph.py - correct by construction. If the
morphology can't produce a certain answer for a given word, build() returns
None and the caller tries another word/template.

Each template: id, concept, cefr, needs(item)->bool, build(item)->exercise|None
An exercise is a dict: {prompt, answer, note, concept}.
"""
from . import morph


def _is_noun_with_gender(item):
    return item.get("pos") == "noun" and item.get("gender") in ("m", "f")


class Template:
    def __init__(self, id, concept, cefr, needs, build):
        self.id = id
        self.concept = concept
        self.cefr = cefr
        self.needs = needs
        self.build = build


def _definite_article(item):
    art = morph.definite_article(item["gender"], "s", item["term"])
    if not art:
        return None
    return {
        "prompt": "Add the definite article:   ___ %s" % item["term"],
        "answer": art,
        "note": "%s is %s singular." % (item["term"],
                                        "masculine" if item["gender"] == "m" else "feminine"),
        "concept": "definite-article",
    }


def _indefinite_article(item):
    art = morph.indefinite_article(item["gender"], item["term"])
    if not art:
        return None
    return {
        "prompt": "Add the indefinite article (a/an):   ___ %s" % item["term"],
        "answer": art,
        "note": "%s is %s." % (item["term"],
                               "masculine" if item["gender"] == "m" else "feminine"),
        "concept": "indefinite-article",
    }


def _plural(item):
    pl = morph.pluralize(item["term"], item["gender"])
    if not pl:
        return None
    return {
        "prompt": "Make it plural:   un/una %s  ->  due ___" % item["term"],
        "answer": pl,
        "note": "Regular %s plural." % ("feminine" if item["gender"] == "f" else "masculine"),
        "concept": "noun-plural",
    }


_PERSONS = [("1s", "io"), ("2s", "tu"), ("3s", "lui/lei"),
            ("1p", "noi"), ("2p", "voi"), ("3p", "loro")]


def _is_verb(item):
    return item.get("pos") == "verb"


def _present_tense(item):
    lemma = (item.get("lemma") or item["term"]).lower()
    if not lemma.endswith(("are", "ere", "ire")):
        return None
    person, label = _PERSONS[len(lemma) % len(_PERSONS)]   # vary by word, deterministic
    form = morph.conjugate(lemma, person=person)
    if not form:
        return None
    return {
        "prompt": "Present tense - conjugate:   %s ___   (%s)" % (label, lemma),
        "answer": form,
        "note": "Present indicative, %s of %s." % (label, lemma),
        "concept": "present-tense",
    }


_CONCEPT_LABEL = {
    "present-tense": "Present tense", "passato-prossimo": "Passato prossimo",
    "imperfetto": "Imperfetto", "futuro": "Future tense",
    "congiuntivo": "Congiuntivo (present)",
    "congiuntivo-imperfetto": "Congiuntivo imperfetto", "conditional": "Conditional",
}


def verb_exercise(item, concept):
    """Fill-in for a verb in a specific tense/mood concept. None if it can't be
    generated (word isn't a regular-looking verb, or morphology unavailable)."""
    lemma = (item.get("lemma") or item["term"]).lower()
    if not lemma.endswith(("are", "ere", "ire")):
        return None
    person, label = _PERSONS[len(lemma) % len(_PERSONS)]
    form = morph.conjugate_concept(lemma, concept, person=person)
    if not form:
        return None
    name = _CONCEPT_LABEL.get(concept, concept)
    return {
        "prompt": "%s - conjugate:   %s ___   (%s)" % (name, label, lemma),
        "answer": form,
        "note": "%s, %s of %s." % (name, label, lemma),
        "concept": concept,
    }


TEMPLATES = [
    Template("def-art", "Definite articles", "A1", _is_noun_with_gender, _definite_article),
    Template("indef-art", "Indefinite articles", "A1", _is_noun_with_gender, _indefinite_article),
    Template("plural", "Noun plurals", "A1", _is_noun_with_gender, _plural),
    Template("present", "Present tense", "A1", _is_verb, _present_tense),
]


def buildable(item):
    """Templates that can actually produce an exercise for this item."""
    out = []
    for t in TEMPLATES:
        if t.needs(item) and t.build(item) is not None:
            out.append(t)
    return out
