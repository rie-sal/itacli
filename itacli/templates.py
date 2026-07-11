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


TEMPLATES = [
    Template("def-art", "Definite articles", "A1", _is_noun_with_gender, _definite_article),
    Template("indef-art", "Indefinite articles", "A1", _is_noun_with_gender, _indefinite_article),
    Template("plural", "Noun plurals", "A1", _is_noun_with_gender, _plural),
]


def buildable(item):
    """Templates that can actually produce an exercise for this item."""
    out = []
    for t in TEMPLATES:
        if t.needs(item) and t.build(item) is not None:
            out.append(t)
    return out
