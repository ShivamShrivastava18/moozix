"""Shared test fixtures."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.schemas import (
    AudioFingerprint,
    TasteProfile,
    TopArtist,
    TopTrack,
    UserPublic,
)


def _artist(id_: str, name: str, genres: list[str], popularity: int = 60) -> TopArtist:
    return TopArtist(id=id_, name=name, genres=genres, popularity=popularity)


def _track(id_: str, name: str, artist_names: list[str], artist_ids: list[str]) -> TopTrack:
    return TopTrack(
        uri=f"spotify:track:{id_}",
        id=id_,
        name=name,
        artist_names=artist_names,
        artist_ids=artist_ids,
        popularity=70,
    )


@pytest.fixture
def profile_alice() -> TasteProfile:
    artists = [
        _artist("a1", "The 1975", ["indie pop", "pop rock"]),
        _artist("a2", "Maroon 5", ["pop", "pop rock"]),
        _artist("a3", "Taylor Swift", ["pop"]),
        _artist("a4", "Lauv", ["pop"]),
        _artist("a5", "Ed Sheeran", ["pop", "uk pop"]),
    ]
    tracks = [
        _track("t1", "About You", ["The 1975"], ["a1"]),
        _track("t2", "Memories", ["Maroon 5"], ["a2"]),
        _track("t3", "Anti-Hero", ["Taylor Swift"], ["a3"]),
    ]
    return TasteProfile(
        user=UserPublic(user_id="alice", display_name="Alice"),
        top_artists_medium=artists,
        top_tracks_medium=tracks,
        genres={"pop": 0.5, "indie pop": 0.2, "pop rock": 0.2, "uk pop": 0.1},
        audio_fingerprint=AudioFingerprint(
            danceability=0.65, energy=0.7, valence=0.55, acousticness=0.2,
            instrumentalness=0.05, liveness=0.15, speechiness=0.08,
            tempo=120.0, loudness=-6.0, sample_size=20,
        ),
        built_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def profile_bob() -> TasteProfile:
    """Has 2 artists in common with alice (pop overlap)."""
    artists = [
        _artist("a1", "The 1975", ["indie pop", "pop rock"]),
        _artist("a3", "Taylor Swift", ["pop"]),
        _artist("b1", "Arctic Monkeys", ["indie rock", "garage rock"]),
        _artist("b2", "Mac DeMarco", ["indie", "lo-fi"]),
    ]
    tracks = [
        _track("t1", "About You", ["The 1975"], ["a1"]),
        _track("b_t1", "Do I Wanna Know?", ["Arctic Monkeys"], ["b1"]),
    ]
    return TasteProfile(
        user=UserPublic(user_id="bob", display_name="Bob"),
        top_artists_medium=artists,
        top_tracks_medium=tracks,
        genres={"indie pop": 0.3, "pop": 0.2, "indie rock": 0.3, "lo-fi": 0.2},
        audio_fingerprint=AudioFingerprint(
            danceability=0.55, energy=0.6, valence=0.5, acousticness=0.3,
            instrumentalness=0.1, liveness=0.18, speechiness=0.07,
            tempo=115.0, loudness=-7.5, sample_size=20,
        ),
        built_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def profile_charlie() -> TasteProfile:
    """Completely disjoint taste from alice."""
    artists = [
        _artist("c1", "Burial", ["dubstep", "uk garage"]),
        _artist("c2", "Aphex Twin", ["idm", "electronica"]),
        _artist("c3", "Boards of Canada", ["idm", "ambient"]),
    ]
    tracks = [
        _track("c_t1", "Archangel", ["Burial"], ["c1"]),
        _track("c_t2", "Windowlicker", ["Aphex Twin"], ["c2"]),
    ]
    return TasteProfile(
        user=UserPublic(user_id="charlie", display_name="Charlie"),
        top_artists_medium=artists,
        top_tracks_medium=tracks,
        genres={"idm": 0.4, "ambient": 0.3, "dubstep": 0.2, "uk garage": 0.1},
        audio_fingerprint=AudioFingerprint(
            danceability=0.3, energy=0.4, valence=0.2, acousticness=0.15,
            instrumentalness=0.7, liveness=0.1, speechiness=0.05,
            tempo=85.0, loudness=-12.0, sample_size=20,
        ),
        built_at=datetime.now(timezone.utc),
    )
