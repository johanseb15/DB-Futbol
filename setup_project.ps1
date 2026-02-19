# setup_project.ps1
# Ejecutar desde C:\Users\Sistemas\Documents\Proyectos
# Crea toda la estructura del proyecto football-db

Write-Host "Creando estructura del proyecto..." -ForegroundColor Cyan

# ── Crear carpetas ────────────────────────────────────────────────────────────
$folders = @(
    "config",
    "db\models",
    "scrapers\sofascore",
    "scrapers\transfermarkt",
    "pipeline",
    "scripts",
    "logs"
)
foreach ($f in $folders) {
    New-Item -ItemType Directory -Force -Path $f | Out-Null
    Write-Host "  [+] $f" -ForegroundColor Green
}

# ── Mover archivos ya descargados al lugar correcto ───────────────────────────
if (Test-Path "matches.py") {
    Move-Item -Force "matches.py" "db\models\matches.py"
    Write-Host "  [~] matches.py -> db\models\matches.py" -ForegroundColor Yellow
}
if (Test-Path "runner.py") {
    Move-Item -Force "runner.py" "pipeline\runner.py"
    Write-Host "  [~] runner.py -> pipeline\runner.py" -ForegroundColor Yellow
}

# ── .env ─────────────────────────────────────────────────────────────────────
@"
DB_USER=football
DB_PASSWORD=football123
DB_NAME=football_data
DB_HOST=localhost
DB_PORT=5432
DATABASE_URL=postgresql+asyncpg://football:football123@localhost:5432/football_data
DATABASE_URL_SYNC=postgresql://football:football123@localhost:5432/football_data
REDIS_URL=redis://localhost:6379/0
CACHE_TTL_SECONDS=3600
SCRAPER_DELAY_SECONDS=8
SCRAPER_MAX_RETRIES=3
SCRAPER_TIMEOUT_SECONDS=30
SCRAPER_CONCURRENCY=3
LOG_LEVEL=INFO
LOG_FILE=logs/football.log
"@ | Set-Content ".env" -Encoding UTF8
Write-Host "  [+] .env" -ForegroundColor Green

# ── requirements.txt ─────────────────────────────────────────────────────────
@"
sqlalchemy==2.0.30
asyncpg==0.29.0
psycopg2-binary==2.9.9
alembic==1.13.1
playwright==1.44.0
beautifulsoup4==4.12.3
httpx==0.27.0
lxml==5.2.2
selectolax==0.3.21
pandas==2.2.2
numpy==1.26.4
pydantic==2.7.1
pydantic-settings==2.2.1
redis==5.0.4
hiredis==2.3.2
celery==5.4.0
python-dotenv==1.0.1
tenacity==8.3.0
rich==13.7.1
loguru==0.7.2
tqdm==4.66.4
arrow==1.3.0
"@ | Set-Content "requirements.txt" -Encoding UTF8
Write-Host "  [+] requirements.txt" -ForegroundColor Green

# ── config/__init__.py ───────────────────────────────────────────────────────
"" | Set-Content "config\__init__.py" -Encoding UTF8

# ── config/settings.py ───────────────────────────────────────────────────────
@"
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    DATABASE_URL:      str  = "postgresql+asyncpg://football:football123@localhost:5432/football_data"
    DATABASE_URL_SYNC: str  = "postgresql://football:football123@localhost:5432/football_data"
    DB_ECHO:           bool = False
    REDIS_URL:         str  = "redis://localhost:6379/0"
    CACHE_TTL_SECONDS: int  = 3600
    SCRAPER_DELAY_SECONDS:  float = 8.0
    SCRAPER_MAX_RETRIES:    int   = 3
    SCRAPER_TIMEOUT_SECONDS:int   = 30
    SCRAPER_CONCURRENCY:    int   = 3
    LOG_LEVEL: str = "INFO"
    LOG_FILE:  str = "logs/football.log"

settings = Settings()
"@ | Set-Content "config\settings.py" -Encoding UTF8
Write-Host "  [+] config/settings.py" -ForegroundColor Green

# ── db/__init__.py ────────────────────────────────────────────────────────────
"" | Set-Content "db\__init__.py" -Encoding UTF8

# ── db/models/base.py ─────────────────────────────────────────────────────────
@"
import uuid
from datetime import datetime
from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

class UUIDMixin:
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
"@ | Set-Content "db\models\base.py" -Encoding UTF8
Write-Host "  [+] db/models/base.py" -ForegroundColor Green

# ── db/models/geography.py ────────────────────────────────────────────────────
@"
import uuid
from typing import Optional
from sqlalchemy import String, Integer, ForeignKey, Boolean, Date, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin, UUIDMixin

class Country(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "countries"
    name:       Mapped[str]           = mapped_column(String(100), nullable=False, unique=True)
    code_iso2:  Mapped[str]           = mapped_column(String(2),   nullable=False, unique=True)
    code_iso3:  Mapped[Optional[str]] = mapped_column(String(3),   nullable=True)
    continent:  Mapped[Optional[str]] = mapped_column(String(50),  nullable=True)
    flag_url:   Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    competitions: Mapped[list["Competition"]] = relationship(back_populates="country")
    teams:        Mapped[list["Team"]]        = relationship(back_populates="country")
    players:      Mapped[list["Player"]]      = relationship(back_populates="nationality")
    venues:       Mapped[list["Venue"]]       = relationship(back_populates="country")

class Competition(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "competitions"
    __table_args__ = (UniqueConstraint("sofascore_id", name="uq_competition_sofascore"),)
    name:             Mapped[str]                  = mapped_column(String(200), nullable=False)
    short_name:       Mapped[Optional[str]]        = mapped_column(String(50),  nullable=True)
    country_id:       Mapped[Optional[uuid.UUID]]  = mapped_column(UUID(as_uuid=True), ForeignKey("countries.id"), nullable=True)
    type:             Mapped[str]                  = mapped_column(String(30),  nullable=False)
    level:            Mapped[int]                  = mapped_column(Integer,     nullable=False, default=1)
    is_active:        Mapped[bool]                 = mapped_column(Boolean,     nullable=False, default=True)
    sofascore_id:     Mapped[Optional[int]]        = mapped_column(Integer,     nullable=True)
    transfermarkt_id: Mapped[Optional[str]]        = mapped_column(String(100), nullable=True)
    fbref_id:         Mapped[Optional[str]]        = mapped_column(String(100), nullable=True)
    api_football_id:  Mapped[Optional[int]]        = mapped_column(Integer,     nullable=True)
    logo_url:         Mapped[Optional[str]]        = mapped_column(String(500), nullable=True)
    country: Mapped[Optional["Country"]] = relationship(back_populates="competitions")
    seasons: Mapped[list["Season"]]      = relationship(back_populates="competition")

class Season(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "seasons"
    __table_args__ = (UniqueConstraint("competition_id", "name", name="uq_season_competition_name"),)
    competition_id: Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), ForeignKey("competitions.id"), nullable=False)
    name:           Mapped[str]             = mapped_column(String(50),  nullable=False)
    start_date:     Mapped[Optional[object]]= mapped_column(Date, nullable=True)
    end_date:       Mapped[Optional[object]]= mapped_column(Date, nullable=True)
    is_current:     Mapped[bool]            = mapped_column(Boolean, nullable=False, default=False)
    sofascore_id:   Mapped[Optional[int]]   = mapped_column(Integer, nullable=True)
    competition: Mapped["Competition"]   = relationship(back_populates="seasons")
    matches:     Mapped[list["Match"]]   = relationship(back_populates="season")

class Venue(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "venues"
    name:        Mapped[str]            = mapped_column(String(200), nullable=False)
    city:        Mapped[Optional[str]]  = mapped_column(String(100), nullable=True)
    country_id:  Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("countries.id"), nullable=True)
    capacity:    Mapped[Optional[int]]  = mapped_column(Integer, nullable=True)
    latitude:    Mapped[Optional[float]]= mapped_column(nullable=True)
    longitude:   Mapped[Optional[float]]= mapped_column(nullable=True)
    sofascore_id:Mapped[Optional[int]]  = mapped_column(Integer, nullable=True)
    country: Mapped[Optional["Country"]] = relationship(back_populates="venues")
    matches: Mapped[list["Match"]]       = relationship(back_populates="venue")
    teams:   Mapped[list["Team"]]        = relationship(back_populates="home_venue")
"@ | Set-Content "db\models\geography.py" -Encoding UTF8
Write-Host "  [+] db/models/geography.py" -ForegroundColor Green

# ── db/models/people.py ───────────────────────────────────────────────────────
@"
import uuid
from typing import Optional
from datetime import date
from sqlalchemy import String, Integer, Float, ForeignKey, Date, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin, UUIDMixin

class Player(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "players"
    name:            Mapped[str]           = mapped_column(String(200), nullable=False)
    full_name:       Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    date_of_birth:   Mapped[Optional[date]]= mapped_column(Date, nullable=True)
    nationality_id:  Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("countries.id"), nullable=True)
    position:        Mapped[Optional[str]] = mapped_column(String(30),  nullable=True)
    position_detail: Mapped[Optional[str]] = mapped_column(String(50),  nullable=True)
    foot:            Mapped[Optional[str]] = mapped_column(String(10),  nullable=True)
    height_cm:       Mapped[Optional[int]] = mapped_column(Integer,     nullable=True)
    weight_kg:       Mapped[Optional[int]] = mapped_column(Integer,     nullable=True)
    photo_url:       Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_active:       Mapped[bool]          = mapped_column(Boolean,     nullable=False, default=True)
    retired_at:      Mapped[Optional[date]]= mapped_column(Date,        nullable=True)
    sofascore_id:     Mapped[Optional[int]] = mapped_column(Integer,     nullable=True, unique=True, index=True)
    transfermarkt_id: Mapped[Optional[str]] = mapped_column(String(50),  nullable=True, unique=True, index=True)
    fbref_id:         Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    api_football_id:  Mapped[Optional[int]] = mapped_column(Integer,     nullable=True)
    wikidata_id:      Mapped[Optional[str]] = mapped_column(String(30),  nullable=True)
    extra:            Mapped[Optional[dict]]= mapped_column(JSONB,       nullable=True)
    nationality:   Mapped[Optional["Country"]]      = relationship(back_populates="players")
    contracts:     Mapped[list["PlayerContract"]]   = relationship(back_populates="player")
    market_values: Mapped[list["MarketValue"]]      = relationship(back_populates="player")
    transfers:     Mapped[list["Transfer"]]         = relationship(back_populates="player")
    match_stats:   Mapped[list["PlayerMatchStats"]] = relationship(back_populates="player")
    match_events:  Mapped[list["MatchEvent"]]       = relationship(back_populates="player")

class Coach(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "coaches"
    name:            Mapped[str]           = mapped_column(String(200), nullable=False)
    date_of_birth:   Mapped[Optional[date]]= mapped_column(Date, nullable=True)
    nationality_id:  Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("countries.id"), nullable=True)
    photo_url:       Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_active:       Mapped[bool]          = mapped_column(Boolean, nullable=False, default=True)
    sofascore_id:    Mapped[Optional[int]] = mapped_column(Integer, nullable=True, unique=True, index=True)
    transfermarkt_id:Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    nationality:  Mapped[Optional["Country"]] = relationship()
    team_seasons: Mapped[list["TeamSeason"]]  = relationship(back_populates="coach")

class Referee(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "referees"
    name:           Mapped[str]           = mapped_column(String(200), nullable=False)
    date_of_birth:  Mapped[Optional[date]]= mapped_column(Date, nullable=True)
    nationality_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("countries.id"), nullable=True)
    is_active:      Mapped[bool]          = mapped_column(Boolean, nullable=False, default=True)
    sofascore_id:   Mapped[Optional[int]] = mapped_column(Integer, nullable=True, unique=True, index=True)
    nationality: Mapped[Optional["Country"]] = relationship()
    matches:     Mapped[list["Match"]]       = relationship(back_populates="referee")
"@ | Set-Content "db\models\people.py" -Encoding UTF8
Write-Host "  [+] db/models/people.py" -ForegroundColor Green

# ── db/models/teams.py ────────────────────────────────────────────────────────
@"
import uuid
from typing import Optional
from datetime import date
from sqlalchemy import String, Integer, ForeignKey, Boolean, Date, UniqueConstraint, SmallInteger
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin, UUIDMixin

class Team(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "teams"
    name:         Mapped[str]           = mapped_column(String(200), nullable=False)
    short_name:   Mapped[Optional[str]] = mapped_column(String(50),  nullable=True)
    full_name:    Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    is_national:  Mapped[bool]          = mapped_column(Boolean, nullable=False, default=False)
    country_id:   Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("countries.id"), nullable=True)
    city:         Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    home_venue_id:Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("venues.id"), nullable=True)
    founded_year: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    colors:       Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    logo_url:     Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_active:    Mapped[bool]          = mapped_column(Boolean, nullable=False, default=True)
    sofascore_id:     Mapped[Optional[int]] = mapped_column(Integer, nullable=True, unique=True, index=True)
    transfermarkt_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, unique=True, index=True)
    fbref_id:         Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    api_football_id:  Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    extra: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    country:       Mapped[Optional["Country"]]   = relationship(back_populates="teams")
    home_venue:    Mapped[Optional["Venue"]]     = relationship(back_populates="teams")
    team_seasons:  Mapped[list["TeamSeason"]]    = relationship(back_populates="team")
    contracts:     Mapped[list["PlayerContract"]]= relationship(back_populates="team")
    home_matches:  Mapped[list["Match"]]         = relationship(foreign_keys="Match.home_team_id", back_populates="home_team")
    away_matches:  Mapped[list["Match"]]         = relationship(foreign_keys="Match.away_team_id", back_populates="away_team")
    transfers_in:  Mapped[list["Transfer"]]      = relationship(foreign_keys="Transfer.to_team_id",   back_populates="to_team")
    transfers_out: Mapped[list["Transfer"]]      = relationship(foreign_keys="Transfer.from_team_id", back_populates="from_team")

class TeamSeason(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "team_seasons"
    __table_args__ = (UniqueConstraint("team_id", "season_id", name="uq_team_season"),)
    team_id:        Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id"),   nullable=False)
    season_id:      Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), ForeignKey("seasons.id"), nullable=False)
    coach_id:       Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("coaches.id"), nullable=True)
    final_position: Mapped[Optional[int]]   = mapped_column(Integer, nullable=True)
    points:         Mapped[Optional[int]]   = mapped_column(Integer, nullable=True)
    matches_played: Mapped[Optional[int]]   = mapped_column(Integer, nullable=True)
    wins:           Mapped[Optional[int]]   = mapped_column(Integer, nullable=True)
    draws:          Mapped[Optional[int]]   = mapped_column(Integer, nullable=True)
    losses:         Mapped[Optional[int]]   = mapped_column(Integer, nullable=True)
    goals_for:      Mapped[Optional[int]]   = mapped_column(Integer, nullable=True)
    goals_against:  Mapped[Optional[int]]   = mapped_column(Integer, nullable=True)
    was_promoted:   Mapped[Optional[bool]]  = mapped_column(Boolean, nullable=True)
    was_relegated:  Mapped[Optional[bool]]  = mapped_column(Boolean, nullable=True)
    team:   Mapped["Team"]            = relationship(back_populates="team_seasons")
    season: Mapped["Season"]          = relationship()
    coach:  Mapped[Optional["Coach"]] = relationship(back_populates="team_seasons")

class PlayerContract(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "player_contracts"
    __table_args__ = (UniqueConstraint("player_id", "team_id", "start_date", name="uq_contract"),)
    player_id:     Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), ForeignKey("players.id"), nullable=False, index=True)
    team_id:       Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id"),   nullable=False, index=True)
    jersey_number: Mapped[Optional[int]]  = mapped_column(SmallInteger, nullable=True)
    start_date:    Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date:      Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_loan:       Mapped[bool]           = mapped_column(Boolean, nullable=False, default=False)
    is_current:    Mapped[bool]           = mapped_column(Boolean, nullable=False, default=False)
    player: Mapped["Player"] = relationship(back_populates="contracts")
    team:   Mapped["Team"]   = relationship(back_populates="contracts")
"@ | Set-Content "db\models\teams.py" -Encoding UTF8
Write-Host "  [+] db/models/teams.py" -ForegroundColor Green

# ── db/models/transfers.py ────────────────────────────────────────────────────
@"
import uuid
from typing import Optional
from datetime import date
from sqlalchemy import String, Integer, BigInteger, ForeignKey, Date, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin, UUIDMixin

class MarketValue(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "market_values"
    player_id:   Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), ForeignKey("players.id"), nullable=False, index=True)
    team_id:     Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=True)
    value_eur:   Mapped[Optional[int]]  = mapped_column(BigInteger, nullable=True)
    recorded_at: Mapped[date]           = mapped_column(Date, nullable=False)
    source:      Mapped[str]            = mapped_column(String(50), nullable=False, default="transfermarkt")
    player_age:  Mapped[Optional[int]]  = mapped_column(Integer, nullable=True)
    player: Mapped["Player"]         = relationship(back_populates="market_values")
    team:   Mapped[Optional["Team"]] = relationship()
    __table_args__ = (Index("ix_market_values_player_date", "player_id", "recorded_at"),)

class Transfer(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "transfers"
    player_id:       Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), ForeignKey("players.id"), nullable=False, index=True)
    from_team_id:    Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=True)
    to_team_id:      Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=True)
    transfer_date:   Mapped[Optional[date]]  = mapped_column(Date, nullable=True, index=True)
    season:          Mapped[Optional[str]]   = mapped_column(String(20), nullable=True)
    type:            Mapped[str]             = mapped_column(String(20), nullable=False, default="permanent")
    fee_eur:         Mapped[Optional[int]]   = mapped_column(BigInteger, nullable=True)
    fee_undisclosed: Mapped[Optional[bool]]  = mapped_column(nullable=True)
    fee_free:        Mapped[Optional[bool]]  = mapped_column(nullable=True)
    loan_end_date:   Mapped[Optional[date]]  = mapped_column(Date, nullable=True)
    loan_buy_option: Mapped[Optional[int]]   = mapped_column(BigInteger, nullable=True)
    market_value_at_transfer: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    source:          Mapped[str]             = mapped_column(String(50), nullable=False, default="transfermarkt")
    transfermarkt_id:Mapped[Optional[str]]   = mapped_column(String(100), nullable=True)
    player:    Mapped["Player"]         = relationship(back_populates="transfers")
    from_team: Mapped[Optional["Team"]] = relationship(foreign_keys=[from_team_id], back_populates="transfers_out")
    to_team:   Mapped[Optional["Team"]] = relationship(foreign_keys=[to_team_id],   back_populates="transfers_in")
"@ | Set-Content "db\models\transfers.py" -Encoding UTF8
Write-Host "  [+] db/models/transfers.py" -ForegroundColor Green

# ── db/models/staging.py ─────────────────────────────────────────────────────
@"
import uuid
from typing import Optional
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, Boolean, Index, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, UUIDMixin

class ScrapeJob(Base, UUIDMixin):
    __tablename__ = "scrape_jobs"
    source:        Mapped[str]            = mapped_column(String(50),   nullable=False)
    entity_type:   Mapped[str]            = mapped_column(String(50),   nullable=False)
    entity_id:     Mapped[str]            = mapped_column(String(100),  nullable=False)
    url:           Mapped[Optional[str]]  = mapped_column(String(1000), nullable=True)
    status:        Mapped[str]            = mapped_column(String(20),   nullable=False, default="pending", index=True)
    started_at:    Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at:   Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at:    Mapped[datetime]       = mapped_column(DateTime(timezone=True), server_default=func.now())
    http_status:   Mapped[Optional[int]]  = mapped_column(Integer, nullable=True)
    error_message: Mapped[Optional[str]]  = mapped_column(Text,    nullable=True)
    retry_count:   Mapped[int]            = mapped_column(Integer, nullable=False, default=0)
    normalized:    Mapped[bool]           = mapped_column(Boolean, nullable=False, default=False)
    normalized_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (
        Index("ix_scrape_jobs_source_entity", "source", "entity_type", "entity_id"),
        Index("ix_scrape_jobs_status_created", "status", "created_at"),
    )

class ScrapeRaw(Base, UUIDMixin):
    __tablename__ = "scrape_raw"
    job_id:      Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    source:      Mapped[str]       = mapped_column(String(50),  nullable=False, index=True)
    entity_type: Mapped[str]       = mapped_column(String(50),  nullable=False, index=True)
    entity_id:   Mapped[str]       = mapped_column(String(100), nullable=False)
    payload:     Mapped[dict]      = mapped_column(JSONB,        nullable=False)
    scraped_at:  Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    __table_args__ = (Index("ix_scrape_raw_source_entity_type", "source", "entity_type", "scraped_at"),)
"@ | Set-Content "db\models\staging.py" -Encoding UTF8
Write-Host "  [+] db/models/staging.py" -ForegroundColor Green

# ── db/models/__init__.py ────────────────────────────────────────────────────
@"
from .base import Base, TimestampMixin, UUIDMixin
from .geography import Country, Competition, Season, Venue
from .people import Player, Coach, Referee
from .teams import Team, TeamSeason, PlayerContract
from .matches import Match, MatchEvent, MatchTeamStats, PlayerMatchStats, MatchLineup
from .transfers import MarketValue, Transfer
from .staging import ScrapeJob, ScrapeRaw

__all__ = [
    "Base",
    "Country", "Competition", "Season", "Venue",
    "Player", "Coach", "Referee",
    "Team", "TeamSeason", "PlayerContract",
    "Match", "MatchEvent", "MatchTeamStats", "PlayerMatchStats", "MatchLineup",
    "MarketValue", "Transfer",
    "ScrapeJob", "ScrapeRaw",
]
"@ | Set-Content "db\models\__init__.py" -Encoding UTF8
Write-Host "  [+] db/models/__init__.py" -ForegroundColor Green

# ── db/session.py ────────────────────────────────────────────────────────────
@"
from contextlib import asynccontextmanager, contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker
from config.settings import settings
from db.models import Base

async_engine = create_async_engine(
    settings.DATABASE_URL, pool_size=10, max_overflow=20, pool_pre_ping=True, echo=settings.DB_ECHO,
)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine, class_=AsyncSession, expire_on_commit=False, autocommit=False, autoflush=False,
)
sync_engine = create_engine(
    settings.DATABASE_URL_SYNC, pool_size=5, max_overflow=10, pool_pre_ping=True, echo=settings.DB_ECHO,
)
SyncSessionLocal = sessionmaker(bind=sync_engine, autocommit=False, autoflush=False)

@asynccontextmanager
async def get_async_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

@contextmanager
def get_sync_session() -> Session:
    with SyncSessionLocal() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise

async def create_all_tables() -> None:
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def drop_all_tables() -> None:
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

async def check_connection() -> bool:
    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"DB connection failed: {e}")
        return False
"@ | Set-Content "db\session.py" -Encoding UTF8
Write-Host "  [+] db/session.py" -ForegroundColor Green

# ── scrapers/__init__.py ──────────────────────────────────────────────────────
"" | Set-Content "scrapers\__init__.py" -Encoding UTF8
"" | Set-Content "scrapers\sofascore\__init__.py" -Encoding UTF8
"" | Set-Content "scrapers\transfermarkt\__init__.py" -Encoding UTF8
"" | Set-Content "pipeline\__init__.py" -Encoding UTF8

# ── scripts/init.sql ─────────────────────────────────────────────────────────
@"
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";
CREATE EXTENSION IF NOT EXISTS "unaccent";
"@ | Set-Content "scripts\init.sql" -Encoding UTF8
Write-Host "  [+] scripts/init.sql" -ForegroundColor Green

Write-Host ""
Write-Host "Estructura creada. Verificando..." -ForegroundColor Cyan
Get-ChildItem -Recurse -File | Select-Object FullName | ForEach-Object { Write-Host "  $($_.FullName)" -ForegroundColor DarkGray }

Write-Host ""
Write-Host "LISTO. Siguiente paso:" -ForegroundColor Green
Write-Host "  python -m venv venv" -ForegroundColor White
Write-Host "  venv\Scripts\activate" -ForegroundColor White
Write-Host "  pip install -r requirements.txt" -ForegroundColor White
