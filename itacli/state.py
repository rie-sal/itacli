"""Home-screen data. For the scaffold these are illustrative defaults; each
value gets wired to the DB / scoring engine as the relevant pillar is built.
"""
from . import db


def home_data():
    """Return the values the home screen renders.

    Placeholder numbers until scoring (§8) and assessments (§9) are live.
    """
    return {
        "day": int(db.get_setting("day_count", "1")),
        "name": db.get_setting("user_name", ""),
        "cefr_level": "B1",
        "cefr_assessed_ago": "3.5h ago",
        # continuous proficiency: band + fraction toward the next band
        "prof_fraction": 0.68,
        "prof_next_band": "B2",
        "skills": {
            "Reading": "B1",
            "Listening": "A2",
            "Grammar": "B1",
            "Vocabulary": "B1",
        },
        "focus": ["Listening", "Congiuntivo", "Prepositions"],
        "plan": [
            ("Grammar", 12),
            ("Reading", 8),
            ("Listening", 6),
            ("Vocab", 4),
        ],
    }
