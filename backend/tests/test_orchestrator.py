"""Integration test for the full orchestrator (without LLM)."""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _isolated_db(monkeypatch, tmp_path):
    """Each test gets its own DuckDB file so save/load doesn't interfere."""
    db_path = tmp_path / "test.duckdb"
    monkeypatch.setenv("DUCKDB_PATH", str(db_path))
    # Reset cached settings + connection
    from app import config, db
    config.get_settings.cache_clear()
    if db._conn is not None:
        try:
            db._conn.close()
        except Exception:
            pass
    db._conn = None
    yield
    if db._conn is not None:
        try:
            db._conn.close()
        except Exception:
            pass
        db._conn = None


async def test_orchestrator_self_compare(profile_alice):
    from app.compatibility.orchestrator import compute_compatibility

    result = await compute_compatibility(
        profile_alice, profile_alice, include_llm=False
    )
    assert result.overall_score > 90
    assert result.overlap.score > 95


async def test_orchestrator_alice_bob(profile_alice, profile_bob):
    from app.compatibility.orchestrator import compute_compatibility

    result = await compute_compatibility(
        profile_alice, profile_bob, include_llm=False
    )
    assert 0 <= result.overall_score <= 100
    assert result.user_a.user_id == "alice"
    assert result.user_b.user_id == "bob"
    assert result.llm is None  # disabled


async def test_orchestrator_alice_charlie(profile_alice, profile_charlie):
    from app.compatibility.orchestrator import compute_compatibility

    result = await compute_compatibility(
        profile_alice, profile_charlie, include_llm=False
    )
    # Disjoint tastes -> low overall score
    assert result.overall_score < 50


async def test_cache_roundtrip(profile_alice, profile_bob):
    from app.compatibility.orchestrator import (
        compute_compatibility,
        get_cached_comparison,
    )

    result = await compute_compatibility(
        profile_alice, profile_bob, include_llm=False
    )
    cached = get_cached_comparison("alice", "bob")
    assert cached is not None
    assert cached.overall_score == result.overall_score
    # Order should not matter (key is sorted)
    cached_reverse = get_cached_comparison("bob", "alice")
    assert cached_reverse is not None
    assert cached_reverse.overall_score == result.overall_score
