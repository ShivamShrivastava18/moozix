"""DuckDB persistence layer.

DuckDB is used as both the OLTP store (users, tokens, profiles cache) and the
analytics store (track features cache, listening events). It's single-process
but plenty fast for our purposes.
"""
from __future__ import annotations

import json
import threading
from contextlib import contextmanager
from typing import Any, Iterator

import duckdb

from .config import get_settings

_lock = threading.Lock()
_conn: duckdb.DuckDBPyConnection | None = None


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id        VARCHAR PRIMARY KEY,           -- spotify user id
    display_name   VARCHAR,
    email          VARCHAR,
    image_url      VARCHAR,
    country        VARCHAR,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS oauth_tokens (
    user_id        VARCHAR PRIMARY KEY,
    access_token   VARCHAR NOT NULL,
    refresh_token  VARCHAR NOT NULL,
    expires_at     TIMESTAMP NOT NULL,
    scope          VARCHAR,
    updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS oauth_states (
    state          VARCHAR PRIMARY KEY,
    code_verifier  VARCHAR NOT NULL,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Cached audio features for tracks (shared across users)
CREATE TABLE IF NOT EXISTS track_features (
    track_uri      VARCHAR PRIMARY KEY,
    track_id       VARCHAR,
    name           VARCHAR,
    artist_ids     VARCHAR,                       -- JSON list
    artist_names   VARCHAR,                       -- JSON list
    popularity     INTEGER,
    duration_ms    INTEGER,
    danceability   DOUBLE,
    energy         DOUBLE,
    valence        DOUBLE,
    acousticness   DOUBLE,
    instrumentalness DOUBLE,
    liveness       DOUBLE,
    speechiness    DOUBLE,
    tempo          DOUBLE,
    loudness       DOUBLE,
    mode           INTEGER,
    key            INTEGER,
    time_signature INTEGER,
    fetched_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Cached artist info (genres are on artists, not tracks)
CREATE TABLE IF NOT EXISTS artist_info (
    artist_id      VARCHAR PRIMARY KEY,
    name           VARCHAR,
    genres         VARCHAR,                       -- JSON list
    popularity     INTEGER,
    image_url      VARCHAR,
    fetched_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Built taste profile per user (JSON blob, cached)
CREATE TABLE IF NOT EXISTS taste_profiles (
    user_id        VARCHAR PRIMARY KEY,
    profile_json   VARCHAR NOT NULL,
    built_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Cached pairwise comparisons
CREATE TABLE IF NOT EXISTS comparisons (
    user_a         VARCHAR NOT NULL,
    user_b         VARCHAR NOT NULL,
    result_json    VARCHAR NOT NULL,
    computed_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_a, user_b)
);
"""


def get_conn() -> duckdb.DuckDBPyConnection:
    """Return the singleton DuckDB connection (thread-safe init)."""
    global _conn
    if _conn is None:
        with _lock:
            if _conn is None:
                settings = get_settings()
                _conn = duckdb.connect(str(settings.duckdb_path_resolved))
                _conn.execute(SCHEMA)
    return _conn


@contextmanager
def cursor() -> Iterator[duckdb.DuckDBPyConnection]:
    """Lock-protected cursor. DuckDB connections are not thread-safe for
    concurrent writes from async tasks, so we serialize access."""
    conn = get_conn()
    with _lock:
        yield conn


def to_json(value: Any) -> str:
    return json.dumps(value, default=str, ensure_ascii=False)


def from_json(value: str | None) -> Any:
    if value is None:
        return None
    return json.loads(value)
