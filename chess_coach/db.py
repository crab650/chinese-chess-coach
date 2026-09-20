"""SQLite connections and schema for local learning records."""

from __future__ import annotations

import sqlite3
from flask import current_app, g


SCHEMA = """
CREATE TABLE IF NOT EXISTS games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    human_side TEXT NOT NULL,
    level TEXT NOT NULL,
    coach_mode TEXT NOT NULL DEFAULT 'independent',
    status TEXT NOT NULL,
    fen TEXT NOT NULL,
    history_json TEXT NOT NULL DEFAULT '[]',
    pending_json TEXT
);
CREATE TABLE IF NOT EXISTS mistakes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL REFERENCES games(id),
    ply INTEGER NOT NULL,
    fen_before TEXT NOT NULL,
    played_move TEXT NOT NULL,
    best_move TEXT NOT NULL,
    best_score INTEGER,
    score_loss INTEGER NOT NULL,
    reason TEXT NOT NULL,
    theme TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    attempts INTEGER NOT NULL DEFAULT 0,
    successes INTEGER NOT NULL DEFAULT 0,
    last_practiced_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_games_updated ON games(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_mistakes_created ON mistakes(created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_mistakes_game_move ON mistakes(game_id, ply, played_move);
CREATE TABLE IF NOT EXISTS opponent_lessons (
    game_id INTEGER NOT NULL REFERENCES games(id),
    ply INTEGER NOT NULL,
    choice TEXT NOT NULL,
    correct INTEGER NOT NULL,
    answered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (game_id, ply)
);
"""


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        connection = sqlite3.connect(current_app.config["DATABASE"], timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        g.db = connection
    return g.db


def init_db() -> None:
    db = get_db()
    db.executescript(SCHEMA)
    columns = {row["name"] for row in db.execute("PRAGMA table_info(games)")}
    if "coach_mode" not in columns:
        db.execute("ALTER TABLE games ADD COLUMN coach_mode TEXT NOT NULL DEFAULT 'independent'")
    db.commit()


def close_db(_error: BaseException | None = None) -> None:
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()
