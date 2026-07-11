"""Study-time tracking (SPECS §9). Assessment cadence is spaced by time
STUDIED, not calendar days. Sessions add their elapsed minutes here."""
import datetime

from . import db

ASSESS_EVERY_MIN = 180   # recommend a CEFR check every ~3 hours of study


def add_minutes(n):
    if n <= 0:
        return
    cur = float(db.get_setting("study_minutes_total", "0"))
    db.set_setting("study_minutes_total", "%.1f" % (cur + n))


def total_minutes():
    return float(db.get_setting("study_minutes_total", "0"))


def minutes_since_last_assessment():
    last = float(db.get_setting("study_minutes_at_last_assessment", "0"))
    return max(0.0, total_minutes() - last)


def mark_assessed():
    db.set_setting("study_minutes_at_last_assessment", "%.1f" % total_minutes())


def assessment_due():
    return minutes_since_last_assessment() >= ASSESS_EVERY_MIN


class Timer:
    """Context manager: adds wall-clock minutes spent in a session to the total."""
    def __enter__(self):
        self._start = datetime.datetime.now()
        return self

    def __exit__(self, *exc):
        delta = (datetime.datetime.now() - self._start).total_seconds() / 60.0
        add_minutes(delta)
        return False
