"""Scoring engines (SPECS §8-9). Deterministic. Stubs for now.

Two INDEPENDENT scores:
  - Proficiency: continuous, always-on. Inputs = exercise results (item CEFR
    difficulty x correctness) + Anki retention/intervals/lapses. Rendered as
    the thermometer (band + fraction toward next band).
  - CEFR: discrete, updated only at periodic assessments spaced by time
    studied.

The thermometer is pure rendering of the Proficiency fraction; no AI in the
score or the graphic. (AI touches only difficulty-tagging of unlabeled
content, via the Tier-2 encoder model.)
"""

BANDS = ["A1", "A2", "B1", "B2", "C1", "C2"]


def proficiency_beta():
    """Crude v1 to ship the moment the Anki bridge returns any stats.

    Returns (band, fraction_toward_next). Placeholder until wired to data.
    """
    # TODO: weighted mix of attempts + Anki retention.
    return "B1", 0.68


def cefr_estimate(assessment_results):
    """Map closed-form assessment results onto a CEFR band. Stub."""
    # TODO: score items by CEFR difficulty; produce per-skill + overall band.
    raise NotImplementedError
