# moozix

> Cross-User Spotify Compatibility Engine — find out how musically compatible you are with someone, with hard data and a witty narrative.

Two users log in with Spotify, the backend builds a rich **taste profile** for each, then runs **four parallel compatibility scorers**:

| Method | What it measures |
| --- | --- |
| **Overlap** | Jaccard on shared artists/tracks + cosine on genre weights |
| **Embedding** | Sentence-transformer similarity over textual taste cards |
| **Audio features** | Cosine + per-feature deltas on the aggregated audio fingerprint (energy, valence, danceability, …) |
| **LLM narrative** | Claude-generated compatibility story with vibes & clashes |

## Stack

- **Backend:** FastAPI · DuckDB · httpx · sentence-transformers · Anthropic Claude
- **Frontend:** React + Vite + getdesign `clay` theme

## Quick start

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env  # fill in Spotify + Anthropic keys
uvicorn app.main:app --reload
```

See [`backend/README.md`](backend/README.md) for full setup.

## Status

In active development. PRs welcome.
