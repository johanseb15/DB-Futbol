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
