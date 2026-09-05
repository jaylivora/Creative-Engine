"""
Database layer for the Creator Analytics Engine.

Uses SQLite for the MVP. Swap the connection logic for Postgres later
by changing `get_connection()` — everything else (schema, queries) stays
the same if you use SQLAlchemy Core down the road, but plain sqlite3 is
kept here for simplicity while you're prototyping.
"""

import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "creator_engine.db")

# Columns added after the initial release. Listed here so init_db() can
# migrate an existing database in place (ALTER TABLE ADD COLUMN) instead
# of requiring you to delete and reseed data/creator_engine.db every time
# the schema grows.
POSTS_NEW_COLUMNS = {
    "estimated_revenue": "REAL",       # projected $ from this post (ad rev share + attributable sponsor value)
    "new_viewers": "INTEGER",          # unique viewers who don't already follow the account
    "new_followers": "INTEGER",        # of those new viewers, how many followed as a result
}

CONTENT_IDEAS_NEW_COLUMNS = {
    "predicted_views": "REAL",
    "predicted_revenue": "REAL",
    "predicted_new_followers": "REAL",
}


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _migrate_posts_table(conn):
    """Add any missing columns to an already-existing posts table so
    older local databases pick up new fields without needing a full reset."""
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(posts)")
    existing_cols = {row["name"] for row in cur.fetchall()}
    for col_name, col_type in POSTS_NEW_COLUMNS.items():
        if col_name not in existing_cols:
            cur.execute(f"ALTER TABLE posts ADD COLUMN {col_name} {col_type}")


def _migrate_content_ideas_table(conn):
    """Same idea as _migrate_posts_table, but for content_ideas — this is
    what was missing before, causing KeyError: 'predicted_views' etc. on
    older databases that had ideas saved before these columns existed."""
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(content_ideas)")
    existing_cols = {row["name"] for row in cur.fetchall()}
    for col_name, col_type in CONTENT_IDEAS_NEW_COLUMNS.items():
        if col_name not in existing_cols:
            cur.execute(f"ALTER TABLE content_ideas ADD COLUMN {col_name} {col_type}")


def init_db():
    """Create tables if they don't exist yet, and migrate older databases
    to pick up new columns. Safe to call every app startup."""
    with get_connection() as conn:
        cur = conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL,          -- 'instagram', 'youtube', 'tiktok', 'linkedin', 'facebook'
            handle TEXT NOT NULL,
            connected INTEGER DEFAULT 0,     -- 0/1, becomes real once OAuth is wired up
            follower_count INTEGER,
            oauth_token TEXT,                -- placeholder for encrypted token storage later
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL,
            platform TEXT NOT NULL,
            post_type TEXT NOT NULL,         -- see utils/mock_data.py PLATFORM_SEGMENTS for the full list per platform
            title TEXT,
            topic TEXT,                      -- content theme/category tag
            posted_at TEXT NOT NULL,         -- ISO timestamp
            duration_seconds INTEGER,        -- null for static/photo posts
            caption_length INTEGER,
            hashtag_count INTEGER,
            views INTEGER,
            likes INTEGER,
            comments INTEGER,
            shares INTEGER,
            saves INTEGER,
            avg_watch_pct REAL,              -- 0-100, null for non-video
            estimated_revenue REAL,          -- projected $ (ad revenue share + attributable sponsor value)
            new_viewers INTEGER,             -- unique viewers who weren't already followers
            new_followers INTEGER,           -- of those, how many converted to a follow
            FOREIGN KEY(account_id) REFERENCES accounts(id)
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS content_ideas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            platform TEXT NOT NULL,
            suggested_format TEXT,
            suggested_length_seconds INTEGER,
            suggested_topic TEXT,
            rationale TEXT,                  -- why the engine suggested this
            predicted_impact REAL,           -- 0-100 score
            effort_level TEXT,               -- 'light', 'medium', 'heavy'
            strategic_fit REAL,              -- 0-100 score
            priority_score REAL,             -- computed composite score
            predicted_views REAL,
            predicted_revenue REAL,
            predicted_new_followers REAL,
            status TEXT DEFAULT 'suggested', -- 'suggested', 'planned', 'dismissed', 'posted'
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)

        _migrate_posts_table(conn)
        _migrate_content_ideas_table(conn)
        conn.commit()


def fetch_df(query, params=()):
    """Convenience helper: run a query and return a pandas DataFrame."""
    import pandas as pd
    with get_connection() as conn:
        return pd.read_sql_query(query, conn, params=params)