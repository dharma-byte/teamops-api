from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration, loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_name: str = "TeamOps API"
    environment: str = "development"  # development | staging | production
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://teamops:teamops@localhost:5432/teamops"

    # Redis / Upstash
    redis_url: str = "redis://localhost:6379/0"

    # Auth
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor — read once per process, reused everywhere via Depends()."""
    return Settings()
