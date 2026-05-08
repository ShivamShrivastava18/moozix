"""Cached enrichment: audio features for tracks, genres for artists.

We cache aggressively in DuckDB so each track/artist is fetched at most once
across the whole system.
"""
from __future__ import annotations

import json
import logging

from ..db import cursor, from_json, to_json
from .client import SpotifyClient

log = logging.getLogger(__name__)


# ---------- Audio features ----------

AUDIO_FEATURE_COLS = [
    "danceability", "energy", "valence", "acousticness",
    "instrumentalness", "liveness", "speechiness",
    "tempo", "loudness", "mode", "key", "time_signature",
]


def _track_uri(track_id: str) -> str:
    return f"spotify:track:{track_id}"


def get_cached_track_features(track_ids: list[str]) -> dict[str, dict]:
    """Return {track_id: feature_row} for tracks already cached."""
    if not track_ids:
        return {}
    uris = [_track_uri(t) for t in track_ids]
    placeholders = ",".join(["?"] * len(uris))
    with cursor() as c:
        rows = c.execute(
            f"""
            SELECT track_id, name, artist_ids, artist_names, popularity, duration_ms,
                   danceability, energy, valence, acousticness, instrumentalness,
                   liveness, speechiness, tempo, loudness, mode, key, time_signature
            FROM track_features WHERE track_uri IN ({placeholders})
            """,
            uris,
        ).fetchall()
    out = {}
    for r in rows:
        out[r[0]] = {
            "track_id": r[0],
            "name": r[1],
            "artist_ids": from_json(r[2]) or [],
            "artist_names": from_json(r[3]) or [],
            "popularity": r[4],
            "duration_ms": r[5],
            "danceability": r[6],
            "energy": r[7],
            "valence": r[8],
            "acousticness": r[9],
            "instrumentalness": r[10],
            "liveness": r[11],
            "speechiness": r[12],
            "tempo": r[13],
            "loudness": r[14],
            "mode": r[15],
            "key": r[16],
            "time_signature": r[17],
        }
    return out


def upsert_track_features(rows: list[dict]) -> None:
    if not rows:
        return
    with cursor() as c:
        for r in rows:
            c.execute(
                """
                INSERT INTO track_features (
                    track_uri, track_id, name, artist_ids, artist_names,
                    popularity, duration_ms,
                    danceability, energy, valence, acousticness,
                    instrumentalness, liveness, speechiness,
                    tempo, loudness, mode, key, time_signature
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (track_uri) DO UPDATE SET
                    name = excluded.name,
                    artist_ids = excluded.artist_ids,
                    artist_names = excluded.artist_names,
                    popularity = excluded.popularity,
                    duration_ms = excluded.duration_ms,
                    danceability = excluded.danceability,
                    energy = excluded.energy,
                    valence = excluded.valence,
                    acousticness = excluded.acousticness,
                    instrumentalness = excluded.instrumentalness,
                    liveness = excluded.liveness,
                    speechiness = excluded.speechiness,
                    tempo = excluded.tempo,
                    loudness = excluded.loudness,
                    mode = excluded.mode,
                    key = excluded.key,
                    time_signature = excluded.time_signature
                """,
                [
                    _track_uri(r["track_id"]),
                    r["track_id"],
                    r.get("name"),
                    to_json(r.get("artist_ids") or []),
                    to_json(r.get("artist_names") or []),
                    r.get("popularity"),
                    r.get("duration_ms"),
                    r.get("danceability"),
                    r.get("energy"),
                    r.get("valence"),
                    r.get("acousticness"),
                    r.get("instrumentalness"),
                    r.get("liveness"),
                    r.get("speechiness"),
                    r.get("tempo"),
                    r.get("loudness"),
                    r.get("mode"),
                    r.get("key"),
                    r.get("time_signature"),
                ],
            )


async def enrich_tracks(
    client: SpotifyClient,
    tracks: list[dict],
) -> dict[str, dict]:
    """Ensure audio features exist for each track. Returns {track_id: features}.

    `tracks` should be raw Spotify track objects (with id, name, artists, popularity, etc.).
    """
    track_ids = [t["id"] for t in tracks if t.get("id")]
    cached = get_cached_track_features(track_ids)
    missing = [tid for tid in track_ids if tid not in cached]

    if missing:
        log.info("Fetching audio features for %d tracks", len(missing))
        features = await client.audio_features_batch(missing)
        # Merge with track metadata
        track_meta = {t["id"]: t for t in tracks if t.get("id")}
        rows = []
        for f in features:
            if not f or "id" not in f:
                continue
            meta = track_meta.get(f["id"], {})
            artists = meta.get("artists") or []
            row = {
                "track_id": f["id"],
                "name": meta.get("name"),
                "artist_ids": [a.get("id") for a in artists if a.get("id")],
                "artist_names": [a.get("name") for a in artists if a.get("name")],
                "popularity": meta.get("popularity"),
                "duration_ms": meta.get("duration_ms") or f.get("duration_ms"),
            }
            for col in AUDIO_FEATURE_COLS:
                row[col] = f.get(col)
            rows.append(row)
        upsert_track_features(rows)
        cached.update({r["track_id"]: r for r in rows})

    return cached


# ---------- Artist genres ----------

def get_cached_artists(artist_ids: list[str]) -> dict[str, dict]:
    if not artist_ids:
        return {}
    placeholders = ",".join(["?"] * len(artist_ids))
    with cursor() as c:
        rows = c.execute(
            f"""
            SELECT artist_id, name, genres, popularity, image_url
            FROM artist_info WHERE artist_id IN ({placeholders})
            """,
            artist_ids,
        ).fetchall()
    return {
        r[0]: {
            "artist_id": r[0],
            "name": r[1],
            "genres": from_json(r[2]) or [],
            "popularity": r[3],
            "image_url": r[4],
        }
        for r in rows
    }


def upsert_artists(artists: list[dict]) -> None:
    if not artists:
        return
    with cursor() as c:
        for a in artists:
            images = a.get("images") or []
            image_url = images[0]["url"] if images else None
            c.execute(
                """
                INSERT INTO artist_info (artist_id, name, genres, popularity, image_url)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (artist_id) DO UPDATE SET
                    name = excluded.name,
                    genres = excluded.genres,
                    popularity = excluded.popularity,
                    image_url = excluded.image_url
                """,
                [
                    a["id"],
                    a.get("name"),
                    to_json(a.get("genres") or []),
                    a.get("popularity"),
                    image_url,
                ],
            )


async def enrich_artists(
    client: SpotifyClient,
    artist_ids: list[str],
) -> dict[str, dict]:
    cached = get_cached_artists(artist_ids)
    missing = [aid for aid in artist_ids if aid not in cached]
    if missing:
        log.info("Fetching info for %d artists", len(missing))
        artists = await client.artists_batch(missing)
        upsert_artists(artists)
        cached.update(get_cached_artists(missing))
    return cached
