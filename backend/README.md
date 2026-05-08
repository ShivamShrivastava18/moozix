# moozix backend

FastAPI service that powers the Cross-User Spotify Compatibility Engine.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Fill in `.env`:

| Var | Where to get it |
| --- | --- |
| `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET` | https://developer.spotify.com/dashboard → Create App. Add `http://127.0.0.1:8000/auth/callback` to Redirect URIs. |
| `ANTHROPIC_API_KEY` | https://console.anthropic.com/ (optional — falls back to a heuristic narrative). |
| `SESSION_SECRET` | Any long random string. `python -c 'import secrets;print(secrets.token_urlsafe(48))'` |

## Run

```bash
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs for the OpenAPI explorer.

## Testing

```bash
pytest -q
```

12 unit + integration tests. The integration suite covers the full orchestrator
(without LLM) on synthetic profiles.

## API surface

| Method | Path | Auth | Notes |
| --- | --- | --- | --- |
| `GET`  | `/auth/login` | - | Redirects to Spotify |
| `GET`  | `/auth/callback` | - | OAuth callback; sets session cookie |
| `GET`  | `/auth/status` | optional | `{authenticated, user?}` |
| `POST` | `/auth/logout` | session | Logs out |
| `GET`  | `/profile/me?refresh=false` | session | Build/load own taste profile |
| `POST` | `/profile/me/refresh` | session | Force rebuild |
| `GET`  | `/profile/{user_id}` | - | Public taste profile |
| `GET`  | `/profile` | - | List users with profiles |
| `POST` | `/compare` | session | `{user_a?, user_b, include_llm, force}` |
| `GET`  | `/compare/{a}/{b}` | - | Cached comparison |

## Architecture

```
app/
├── auth/                # OAuth (PKCE) + signed-cookie sessions
├── spotify/             # Web-API client + cached enrichment
├── profile/             # TasteProfile builder
├── compatibility/       # 4 scorers + orchestrator
│   ├── overlap.py        # Jaccard/cosine on artists, tracks, genres
│   ├── embeddings.py     # sentence-transformers similarity
│   ├── audio_features.py # cosine + per-feature deltas
│   ├── llm_report.py     # Claude narrative
│   └── orchestrator.py   # weighted combination + cache
├── routers/             # FastAPI route handlers
├── db.py                # DuckDB schema + connection
├── schemas.py           # Pydantic models exposed to UI
└── main.py              # FastAPI app
```

### How a comparison runs

1. Frontend `POST /compare {user_b: "..."}` with session cookie.
2. Both profiles are loaded (or built fresh from Spotify if missing/stale).
3. `compute_compatibility` runs the three numeric scorers concurrently
   (`asyncio.to_thread`), then awaits the LLM narrative.
4. Numeric scores are weighted (`overlap 0.45 + embedding 0.30 + audio 0.25`)
   into an `overall_score` (0–100).
5. The full `CompatibilityResult` is cached in `comparisons` (sorted-pair PK).

### Caching strategy

- **`track_features`** — every track URI's audio features are cached forever.
- **`artist_info`** — every artist's genres/popularity cached forever.
- **`taste_profiles`** — one JSON blob per user, rebuilt on demand.
- **`comparisons`** — pairwise, refreshed via `force=true`.

This means after the first compare, repeats are instant.
