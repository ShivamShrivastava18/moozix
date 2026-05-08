"""Tests for the overlap-based compatibility scorer."""
from __future__ import annotations

from app.compatibility.overlap import compute_overlap


def test_self_overlap_is_perfect(profile_alice):
    result = compute_overlap(profile_alice, profile_alice)
    assert result.artist_jaccard == 1.0
    assert result.track_jaccard == 1.0
    assert result.genre_cosine > 0.99
    assert result.score > 95


def test_partial_overlap_alice_bob(profile_alice, profile_bob):
    result = compute_overlap(profile_alice, profile_bob)
    # 2 artists in common (a1, a3) out of 7 union -> jaccard = 2/7
    assert 0.25 < result.artist_jaccard < 0.35
    assert any(a.id == "a1" for a in result.shared_artists)
    assert any(a.id == "a3" for a in result.shared_artists)
    assert "pop" in result.shared_genres
    assert 20 < result.score < 70


def test_disjoint_alice_charlie(profile_alice, profile_charlie):
    result = compute_overlap(profile_alice, profile_charlie)
    assert result.artist_jaccard == 0.0
    assert result.track_jaccard == 0.0
    assert len(result.shared_artists) == 0
    assert result.score < 15


def test_score_in_range(profile_alice, profile_bob):
    result = compute_overlap(profile_alice, profile_bob)
    assert 0 <= result.score <= 100
