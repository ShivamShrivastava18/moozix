"""Overlap-based compatibility scoring.

Computes:
  - Jaccard index on top artists (across all time ranges, deduped)
  - Jaccard index on top tracks
  - Cosine similarity on genre weight vectors
Combined into a single 0..100 score.
"""
from __future__ import annotations

import math

from ..schemas import OverlapBreakdown, TasteProfile, TopArtist, TopTrack


def _all_artists(profile: TasteProfile) -> dict[str, TopArtist]:
    out: dict[str, TopArtist] = {}
    for arr in (profile.top_artists_short, profile.top_artists_medium, profile.top_artists_long):
        for a in arr:
            out.setdefault(a.id, a)
    return out


def _all_tracks(profile: TasteProfile) -> dict[str, TopTrack]:
    out: dict[str, TopTrack] = {}
    for arr in (profile.top_tracks_short, profile.top_tracks_medium, profile.top_tracks_long):
        for t in arr:
            out.setdefault(t.id, t)
    return out


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


def _cosine(d1: dict[str, float], d2: dict[str, float]) -> float:
    if not d1 or not d2:
        return 0.0
    keys = set(d1) | set(d2)
    dot = sum(d1.get(k, 0.0) * d2.get(k, 0.0) for k in keys)
    n1 = math.sqrt(sum(v * v for v in d1.values()))
    n2 = math.sqrt(sum(v * v for v in d2.values()))
    if n1 == 0 or n2 == 0:
        return 0.0
    return dot / (n1 * n2)


def compute_overlap(a: TasteProfile, b: TasteProfile) -> OverlapBreakdown:
    a_artists = _all_artists(a)
    b_artists = _all_artists(b)
    a_tracks = _all_tracks(a)
    b_tracks = _all_tracks(b)

    artist_jaccard = _jaccard(set(a_artists), set(b_artists))
    track_jaccard = _jaccard(set(a_tracks), set(b_tracks))
    genre_cosine = _cosine(a.genres, b.genres)

    # Shared lists for UI evidence
    shared_artist_ids = set(a_artists) & set(b_artists)
    shared_track_ids = set(a_tracks) & set(b_tracks)
    shared_genres = sorted(
        set(a.genres) & set(b.genres),
        key=lambda g: -(a.genres.get(g, 0) + b.genres.get(g, 0)),
    )[:15]

    shared_artists = [a_artists[i] for i in shared_artist_ids][:20]
    # Sort shared artists by combined popularity
    shared_artists.sort(key=lambda x: -(x.popularity or 0))

    shared_tracks = [a_tracks[i] for i in shared_track_ids][:20]
    shared_tracks.sort(key=lambda x: -(x.popularity or 0))

    # Weighted blend: artists matter most (specific signal), then genres, then tracks
    # Track Jaccard is usually small, so we boost it.
    score_raw = (
        0.45 * artist_jaccard
        + 0.35 * genre_cosine
        + 0.20 * min(1.0, track_jaccard * 3)
    )
    # Shared-artist bonus to reward "people who know the same niche stuff"
    bonus = min(0.15, len(shared_artist_ids) / 100)
    score = round(min(1.0, score_raw + bonus) * 100, 2)

    return OverlapBreakdown(
        score=score,
        artist_jaccard=round(artist_jaccard, 4),
        track_jaccard=round(track_jaccard, 4),
        genre_cosine=round(genre_cosine, 4),
        shared_artists=shared_artists,
        shared_tracks=shared_tracks,
        shared_genres=shared_genres,
    )
