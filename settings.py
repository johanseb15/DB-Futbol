"""
Centralized settings loaded from .env file.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL:      str = "postgresql+asyncpg://football:football123@localhost:5432/football_data"
    DATABASE_URL_SYNC: str = "postgresql://football:football123@localhost:5432/football_data"
    DB_ECHO:           bool = False

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL:         str = "redis://localhost:6379/0"
    CACHE_TTL_SECONDS: int = 3600

    # ── Scraping behaviour ────────────────────────────────────────────────────
    SCRAPER_DELAY_SECONDS:  float = 8.0     # min wait between requests to same domain
    SCRAPER_MAX_RETRIES:    int   = 3
    SCRAPER_TIMEOUT_SECONDS:int   = 30
    SCRAPER_CONCURRENCY:    int   = 3       # max parallel scrapers

    # ── Logging ───────────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_FILE:  str = "logs/football.log"


settings = Settings()
