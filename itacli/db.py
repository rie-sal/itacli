"""SQLite schema and initialization. The single structured source (SPECS §5).

The scaffold creates the full schema now so every pillar has a home to grow
into, even while the pillars themselves are stubs.
"""
import sqlite3

from . import paths

SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
    id            INTEGER PRIMARY KEY,
    url           TEXT NOT NULL,
    type          TEXT NOT NULL,      -- gutenberg|liberliber|wikisource|reddit|youtube|film|grammar
    language      TEXT NOT NULL DEFAULT 'it',
    license       TEXT,
    last_scraped  TEXT
);

CREATE TABLE IF NOT EXISTS content_items (
    id            INTEGER PRIMARY KEY,
    source_id     INTEGER REFERENCES sources(id),
    type          TEXT NOT NULL,      -- passage|video|grammar_drill|cefr_item
    skill         TEXT,               -- reading|listening|grammar|vocabulary
    cefr_level    TEXT,               -- A1..C2, or NULL until tagged
    topic         TEXT,
    difficulty    REAL,
    body          TEXT,
    answer_key    TEXT,
    consumed      INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS vocab (
    id            INTEGER PRIMARY KEY,
    term          TEXT NOT NULL,
    lemma         TEXT,
    gloss         TEXT,
    source_context TEXT,
    status        TEXT NOT NULL DEFAULT 'new',  -- new|learning|known
    anki_note_id  INTEGER,
    added_from    TEXT                          -- reading|capture|manual
);

CREATE TABLE IF NOT EXISTS attempts (
    id             INTEGER PRIMARY KEY,
    content_item_id INTEGER REFERENCES content_items(id),
    correct        INTEGER,
    timestamp      TEXT,
    concept_tags   TEXT
);

CREATE TABLE IF NOT EXISTS proficiency_state (
    id       INTEGER PRIMARY KEY,
    key      TEXT UNIQUE NOT NULL,   -- 'overall' | skill name | grammar concept
    score    REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS assessments (
    id                 INTEGER PRIMARY KEY,
    timestamp          TEXT,
    study_minutes_at_time INTEGER,
    cefr_reading       TEXT,
    cefr_listening     TEXT,
    cefr_grammar       TEXT,
    cefr_vocabulary    TEXT,
    cefr_overall       TEXT,
    item_ids_used      TEXT
);

CREATE TABLE IF NOT EXISTS settings (
    key    TEXT PRIMARY KEY,
    value  TEXT
);
"""

DEFAULT_SETTINGS = {
    "time_budget_min": "30",
    "ratio_mode": "auto",           # auto | manual
    "interests": "",                # comma-separated, drives subreddit search
    "study_minutes_total": "0",
    "day_count": "1",
    "capture_hotkey": "<cmd>+<shift>+i",   # the single do-everything shortcut
    "translate_shortcut": "itacli Translate",  # macOS Shortcut used for glosses
    "anki_deck": "itacli",
    "user_name": "",
}


def connect():
    conn = sqlite3.connect(paths.db_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the schema and seed default settings if absent."""
    conn = connect()
    try:
        conn.executescript(SCHEMA)
        for k, v in DEFAULT_SETTINGS.items():
            conn.execute(
                "INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)", (k, v)
            )
        conn.commit()
    finally:
        conn.close()


def get_setting(key, default=None):
    conn = connect()
    try:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default
    finally:
        conn.close()


def set_setting(key, value):
    conn = connect()
    try:
        conn.execute(
            "INSERT INTO settings(key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, str(value)),
        )
        conn.commit()
    finally:
        conn.close()
