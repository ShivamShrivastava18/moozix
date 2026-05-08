"""Application configuration loaded from environment variables."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Spotify OAuth
    spotify_client_id: str = ""
    spotify_client_secret: str = ""
    spotify_redirect_uri: str = "http://127.0.0.1:8000/auth/callback"

    # Frontend
    frontend_url: str = "http://localhost:5173"

    # Anthropic
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5"

    # Session
    session_secret: str = "dev-secret-change-me"

    # Storage
    duckdb_path: str = "./data/moozix.duckdb"

    # Embeddings
    embedding_model: str = "all-MiniLM-L6-v2"

    # Spotify API scopes
    spotify_scopes: str = (
        "user-read-email user-read-private "
        "user-top-read user-library-read "
        "user-read-recently-played playlist-read-private"
    )

    @property
    def duckdb_path_resolved(self) -> Path:
        path = Path(self.duckdb_path).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
