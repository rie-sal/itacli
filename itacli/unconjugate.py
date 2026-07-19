"""Reliable verb un-conjugation (form -> infinitive).

spaCy's lemmatiser is shaky on isolated irregular Italian verbs ('vado' stayed
'vado'). mlconjug3, by contrast, conjugates CORRECTLY - so we run it FORWARD over
a list of common verbs and index every form back to its infinitive. Lookups are
then exact and deterministic. Built once, cached to the profile's data dir.

Falls back to spaCy/heuristic for verbs outside the list (mostly regulars, which
spaCy handles). Adding Morph-it! later would extend coverage to every verb.
"""
import json
import os

from . import paths

# Common Italian verbs (heavy on the irregulars a learner actually meets).
VERBS = """essere avere fare dire andare potere dovere volere sapere stare dare
vedere venire parlare trovare sentire lasciare prendere guardare credere mettere
portare chiedere tenere capire restare passare sembrare pensare tornare cominciare
chiamare vivere entrare ricordare conoscere arrivare diventare morire uscire
scrivere perdere aspettare aprire offrire leggere bere correre rimanere scegliere
chiudere nascere muovere piacere mangiare dormire finire lavorare giocare studiare
amare cantare comprare vendere pagare viaggiare guidare camminare cucinare pulire
aiutare cercare usare cambiare seguire salire scendere spegnere accendere spendere
decidere ridere piangere vincere crescere riuscire produrre condurre tradurre
porre raccogliere cogliere togliere valere bastare servire riflettere""".split()

_INDEX = None


def _cache_path():
    return os.path.join(paths.get_data_dir(), "unconjugate_index.json")


def _build():
    """form -> infinitive for every conjugated form of VERBS."""
    from . import morph
    conj = morph._conjugator()
    index = {}
    if not conj:
        return index
    for inf in VERBS:
        try:
            info = conj.conjugate(inf).conjug_info
        except Exception:
            continue
        for mood in info.values():
            for tense in mood.values():
                if isinstance(tense, dict):
                    for form in tense.values():
                        if form and isinstance(form, str):
                            # last word handles compound tenses ("sono andato")
                            index.setdefault(form.split()[-1].lower(), inf)
        index[inf] = inf
    return index


def _index():
    global _INDEX
    if _INDEX is None:
        try:
            with open(_cache_path(), encoding="utf-8") as f:
                _INDEX = json.load(f)
        except (OSError, ValueError):
            _INDEX = _build()
            try:
                with open(_cache_path(), "w", encoding="utf-8") as f:
                    json.dump(_INDEX, f)
            except OSError:
                pass
    return _INDEX


def infinitive(word):
    """Return the infinitive for a conjugated form, or None if not in the index."""
    if not word:
        return None
    return _index().get(word.strip().lower())
