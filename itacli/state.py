"""Home-screen data - all pulled from the DB, so a fresh user sees zeros, not
fabricated progress. CEFR and per-skill scores stay blank until the assessment
and scoring engines exist (SPECS §8-9)."""
from . import db


def _clean_concept(tag):
    return (tag.split(":")[-1] if ":" in tag else tag).replace("-", " ")


def home_data():
    conn = db.connect()
    try:
        vocab_count = conn.execute("SELECT COUNT(*) FROM vocab").fetchone()[0]
        total, correct = conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(correct), 0) FROM attempts"
        ).fetchone()
        weak = [
            _clean_concept(r[0]) for r in conn.execute(
                "SELECT concept_tags, SUM(CASE WHEN correct=0 THEN 1 ELSE 0 END) m "
                "FROM attempts WHERE concept_tags IS NOT NULL "
                "GROUP BY concept_tags HAVING m > 0 ORDER BY m DESC LIMIT 3"
            ).fetchall()
        ]
        asmt = conn.execute(
            "SELECT cefr_overall, timestamp FROM assessments ORDER BY id DESC LIMIT 1"
        ).fetchone()
    finally:
        conn.close()
    from . import scoring, daily
    prof_fraction, prof_label, _ = scoring.proficiency_beta()
    plan = daily.build_plan()
    return {
        "name": db.get_setting("user_name", ""),
        "day": int(db.get_setting("day_count", "1")),
        "time_budget": int(float(db.get_setting("time_budget_min", "30"))),
        "vocab_count": vocab_count,
        "attempts_total": total,
        "prof_fraction": prof_fraction,
        "prof_label": prof_label,
        "plan": plan,
        "weak": weak,
        "cefr_level": asmt[0] if asmt else None,
        "cefr_assessed": (asmt[1][:10] if asmt and asmt[1] else None),
    }
