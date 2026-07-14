"""Curated, CEFR-tagged item bank for the assessment (SPECS §9).

Closed-form (multiple-choice), auto-graded, no speaking. Deterministic and
correct-by-authoring. A starter bank spanning A1-B2; the template engine and
LLM-authored items can extend it later. Each item:
  {id, cefr, skill, q, choices, answer}
"""
ITEMS = [
    # ---- A1 ----
    {"id": "a1-1", "cefr": "A1", "skill": "grammar",
     "q": "___ ragazzo è alto.", "choices": ["Il", "La", "Lo", "L'"], "answer": "Il"},
    {"id": "a1-2", "cefr": "A1", "skill": "vocabulary",
     "q": "Buongiorno! Come ti ___?",
     "choices": ["chiami", "chiama", "chiamo", "chiamano"], "answer": "chiami"},
    {"id": "a1-3", "cefr": "A1", "skill": "grammar",
     "q": "Ho due ___.", "choices": ["cani", "cane", "canos", "canii"], "answer": "cani"},
    {"id": "a1-4", "cefr": "A1", "skill": "vocabulary",
     "q": "Il contrario di 'grande' è ___.",
     "choices": ["piccolo", "alto", "lungo", "nuovo"], "answer": "piccolo"},
    {"id": "a1-5", "cefr": "A1", "skill": "grammar",
     "q": "Io ___ italiano.", "choices": ["sono", "sei", "è", "siamo"], "answer": "sono"},
    # ---- A2 ----
    {"id": "a2-1", "cefr": "A2", "skill": "grammar",
     "q": "Ieri (io) ___ al cinema.",
     "choices": ["sono andato", "ho andato", "sono andare", "andavo"],
     "answer": "sono andato"},
    {"id": "a2-2", "cefr": "A2", "skill": "grammar",
     "q": "Mi piace ___ la musica.",
     "choices": ["ascoltare", "ascolto", "ascoltando", "ascoltato"], "answer": "ascoltare"},
    {"id": "a2-3", "cefr": "A2", "skill": "vocabulary",
     "q": "Quando ho fame, ___.",
     "choices": ["mangio", "dormo", "bevo", "corro"], "answer": "mangio"},
    {"id": "a2-4", "cefr": "A2", "skill": "grammar",
     "q": "Vado ___ Roma domani.", "choices": ["a", "in", "di", "da"], "answer": "a"},
    {"id": "a2-5", "cefr": "A2", "skill": "grammar",
     "q": "Lei è più alta ___ me.", "choices": ["di", "che", "come", "da"], "answer": "di"},
    # ---- B1 ----
    {"id": "b1-1", "cefr": "B1", "skill": "grammar",
     "q": "Penso che lui ___ ragione.",
     "choices": ["abbia", "ha", "avere", "aveva"], "answer": "abbia"},
    {"id": "b1-2", "cefr": "B1", "skill": "grammar",
     "q": "Mentre ___, ho sentito un rumore.",
     "choices": ["dormivo", "ho dormito", "dormii", "dormirò"], "answer": "dormivo"},
    {"id": "b1-3", "cefr": "B1", "skill": "vocabulary",
     "q": "Un sinonimo di 'veloce' è ___.",
     "choices": ["rapido", "lento", "pigro", "stanco"], "answer": "rapido"},
    {"id": "b1-4", "cefr": "B1", "skill": "grammar",
     "q": "Hai visto Maria? Sì, ___ ho vista.",
     "choices": ["l'", "gli", "le", "li"], "answer": "l'"},
    {"id": "b1-5", "cefr": "B1", "skill": "grammar",
     "q": "Se avessi tempo, ___ di più.",
     "choices": ["viaggerei", "viaggiavo", "viaggerò", "viaggiassi"], "answer": "viaggerei"},
    # ---- B2 ----
    {"id": "b2-1", "cefr": "B2", "skill": "grammar",
     "q": "Vorrei che tu ___ qui con noi.",
     "choices": ["fossi", "sei", "eri", "sarai"], "answer": "fossi"},
    {"id": "b2-2", "cefr": "B2", "skill": "vocabulary",
     "q": "'Sfortunatamente' vuol dire ___.",
     "choices": ["purtroppo", "fortunatamente", "velocemente", "raramente"],
     "answer": "purtroppo"},
    {"id": "b2-3", "cefr": "B2", "skill": "grammar",
     "q": "La lettera ___ scritta da Marco.",
     "choices": ["è stata", "ha", "è", "aveva"], "answer": "è stata"},
    {"id": "b2-4", "cefr": "B2", "skill": "grammar",
     "q": "Benché ___ stanco, ha continuato a lavorare.",
     "choices": ["fosse", "era", "è", "sarà"], "answer": "fosse"},
    {"id": "b2-5", "cefr": "B2", "skill": "vocabulary",
     "q": "L'espressione 'In bocca al lupo' significa ___.",
     "choices": ["buona fortuna", "stai attento", "ho fame", "che peccato"],
     "answer": "buona fortuna"},
]

# Which grammar concept each item exercises (for concept-mastery tracking).
# Items not listed are vocabulary items.
CONCEPT_BY_ID = {
    "a1-1": "articles", "a1-3": "noun-plural", "a1-5": "present-tense",
    "a2-1": "passato-prossimo", "a2-2": "present-tense", "a2-4": "prepositions",
    "a2-5": "comparatives", "b1-1": "congiuntivo", "b1-2": "imperfetto",
    "b1-4": "pronouns", "b1-5": "conditional",
    "b2-1": "congiuntivo-imperfetto", "b2-3": "passive",
    "b2-4": "congiuntivo-imperfetto",
}

LEVELS = ["A1", "A2", "B1", "B2"]


def by_level():
    out = {lvl: [] for lvl in LEVELS}
    for it in ITEMS:
        out[it["cefr"]].append(it)
    return out
