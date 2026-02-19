from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    DATABASE_URL: str = "postgresql+asyncpg://football:football123@localhost:5432/football_data"
    DATABASE_URL_SYNC: str = "postgresql+psycopg://football:football123@localhost:5432/football_data"
    DB_ECHO: bool = False

    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL_SECONDS: int = 3600

    SCRAPER_DELAY_SECONDS: float = 8.0
    SCRAPER_MAX_RETRIES: int = 3
    SCRAPER_TIMEOUT_SECONDS: int = 30
    SCRAPER_CONCURRENCY: int = 3

    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/football.log"

    KPI_FRESHNESS_MAX_SECONDS: float = 300.0
    KPI_QUALITY_HIGH_MAX: float = 0.0
    KPI_MART_RAW_MIN_RATIO: float = 1.0
    KPI_COVERAGE_MIN_RATIO: float = 0.70
    KPI_COVERAGE_COMPETITION_MIN_RATIO: float = 0.70
    KPI_CONTENT_COVERAGE_COMPETITION_MIN_RATIO: float = 0.70
    KPI_MTTR_MAX_SECONDS: float = 1800.0

    API_KEY_HEADER: str = "X-API-Key"
    API_KEY_ENFORCE_PREMIUM: bool = True
    API_RATE_LIMIT_ENABLED: bool = True
    API_DEFAULT_RATE_LIMIT_PER_MINUTE: int = 120

    # Comma-separated list consumed by api/main.py
    CORS_ORIGINS: str = "http://127.0.0.1:3000,http://localhost:3000"


settings = Settings()
